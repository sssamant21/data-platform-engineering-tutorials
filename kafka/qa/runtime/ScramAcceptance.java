import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermission;
import java.security.*;
import java.security.cert.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import javax.net.ssl.*;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.errors.*;

/** Passwords are read only inside this process from restricted mounted Secrets. */
public class ScramAcceptance {
  static String bootstrap,user,phase;
  static void check(boolean ok,String message) {if(!ok)throw new IllegalStateException(message);}
  static void pass(String name) {System.out.println("CHECK:"+phase+"_"+name+":PASS");}
  static String password() throws Exception {
    Path file=Path.of("/identity/password");Set<PosixFilePermission> mode=Files.getPosixFilePermissions(file);
    check(!mode.contains(PosixFilePermission.OTHERS_READ) && !mode.contains(PosixFilePermission.OTHERS_WRITE),"Credential file world accessible");
    return Files.readString(file).trim();
  }
  static String escaped(String value) {return value.replace("\\","\\\\").replace("\"","\\\"");}
  static Properties properties(String username,String password) throws Exception {
    Properties p=new Properties();p.put("bootstrap.servers",bootstrap);p.put("security.protocol","SASL_SSL");
    p.put("sasl.mechanism","SCRAM-SHA-512");p.put("ssl.endpoint.identification.algorithm","https");
    p.put("ssl.truststore.type","PEM");p.put("ssl.truststore.certificates",Files.readString(Path.of("/trust/ca.crt")));
    p.put("sasl.jaas.config","org.apache.kafka.common.security.scram.ScramLoginModule required username=\""+escaped(username)+"\" password=\""+escaped(password)+"\";");
    p.put("default.api.timeout.ms","15000");p.put("request.timeout.ms","8000");return p;
  }
  static void rejected(String username,String password,String outcome) throws Exception {
    boolean failed=false;
    try(Admin admin=Admin.create(properties(username,password))) {
      try {admin.describeCluster().nodes().get(18,TimeUnit.SECONDS);}
      catch(ExecutionException e) {check(e.getCause() instanceof SaslAuthenticationException,"Expected classified SASL authentication rejection");failed=true;}
    }
    check(failed,"Invalid credential unexpectedly authenticated");System.out.println("OBS:SASL_NEGATIVE:"+outcome+":SaslAuthenticationException");
  }
  static void wrongTrust() throws Exception {
    URI endpoint=URI.create("ssl://"+bootstrap);ExecutorService dns=Executors.newSingleThreadExecutor(r->{Thread t=new Thread(r,"scram-dns");t.setDaemon(true);return t;});
    InetAddress address;
    try {address=dns.submit(()->InetAddress.getByName(endpoint.getHost())).get(10,TimeUnit.SECONDS);} finally {dns.shutdownNow();}
    SSLContext wrong=SSLContext.getInstance("TLS");TrustManagerFactory tm=TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());tm.init((KeyStore)null);wrong.init(null,tm.getTrustManagers(),null);
    boolean rejected=false;Socket raw=new Socket();raw.connect(new InetSocketAddress(address,endpoint.getPort()),5000);raw.setSoTimeout(5000);
    try(SSLSocket tls=(SSLSocket)wrong.getSocketFactory().createSocket(raw,endpoint.getHost(),endpoint.getPort(),true)) {
      tls.setSoTimeout(5000);SSLParameters params=tls.getSSLParameters();params.setEndpointIdentificationAlgorithm("HTTPS");tls.setSSLParameters(params);
      try {tls.startHandshake();} catch(SSLException expected) {rejected=true;System.out.println("OBS:TLS_NEGATIVE:UNTRUSTED_CA:"+expected.getClass().getSimpleName());}
    } finally {if(!raw.isClosed())raw.close();}
    check(rejected,"Untrusted CA unexpectedly succeeded");
  }
  public static void main(String[] args) throws Exception {
    bootstrap=args[0];user=args[1];String allowed=args[2],denied=args[3],group=args[4];phase=args[5];int start=Integer.parseInt(args[6]);String secret=password();
    if(phase.equals("stale")) {rejected(user,secret,"STALE_PASSWORD");pass("old_password_rejected_after_rotation");return;}
    try(Admin admin=Admin.create(properties(user,secret))) {
      String cluster=admin.describeCluster().clusterId().get(18,TimeUnit.SECONDS);Collection<Node> nodes=admin.describeCluster().nodes().get(18,TimeUnit.SECONDS);
      check(nodes.size()==3,"Expected three advertised brokers");Set<Integer> ids=new HashSet<>();
      for(Node node:nodes) {
        check(node.port()==9095 && ids.add(node.id()),"Unexpected SASL listener or duplicate broker");
        Properties direct=properties(user,secret);direct.put("bootstrap.servers",node.host()+":"+node.port());
        try(Admin broker=Admin.create(direct)) {check(cluster.equals(broker.describeCluster().clusterId().get(18,TimeUnit.SECONDS)),"Direct authenticated broker identity mismatch");}
        System.out.println("OBS:SASL_ENDPOINT:"+node.id()+":"+node.host()+":"+node.port()+":TLS_HOSTNAME_VERIFIED:SCRAM-SHA-512");
      }
      pass("sasl_ssl_all_advertised_brokers_hostname_verified");
      rejected(user,secret+"-deliberately-invalid","WRONG_PASSWORD");pass("wrong_password_classified_sasl_failure");
      rejected(user+"-unknown",secret,"WRONG_USERNAME");pass("wrong_username_classified_sasl_failure");
      wrongTrust();pass("wrong_ca_classified_tls_failure_before_sasl");
      TopicDescription topic=admin.describeTopics(List.of(allowed)).allTopicNames().get(18,TimeUnit.SECONDS).get(allowed);
      check(topic.partitions().size()==3,"Unexpected partition count");
      for(TopicPartitionInfo part:topic.partitions())check(part.leader()!=null && part.leader().id()>=0 && part.replicas().size()==3 && part.isr().size()==3,"Degraded topic durability");
      Properties pp=properties(user,secret);pp.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");pp.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");
      pp.put("acks","all");pp.put("enable.idempotence","true");pp.put("max.block.ms","15000");pp.put("delivery.timeout.ms","30000");
      try(KafkaProducer<String,String> negative=new KafkaProducer<>(pp)) {
        boolean deniedOk=false;try {negative.send(new ProducerRecord<>(denied,0,"key","must-not-write")).get(20,TimeUnit.SECONDS);}
        catch(ExecutionException e) {check(e.getCause() instanceof TopicAuthorizationException,"Expected topic authorization rejection after authentication");deniedOk=true;}
        check(deniedOk,"Identity exceeded literal topic ACL");pass("authenticated_identity_unauthorized_topic_denied");
      }
      try(KafkaProducer<String,String> producer=new KafkaProducer<>(pp)) {
        for(int i=start;i<start+6;i++) {RecordMetadata m=producer.send(new ProducerRecord<>(allowed,i%3,"key-"+(i%3),user+"-scram-"+i)).get(35,TimeUnit.SECONDS);check(m.offset()==i/3,"Unexpected acknowledged record offset");}
      }
      Properties cp=properties(user,secret);cp.put("group.id",group);cp.put("enable.auto.commit","false");cp.put("auto.offset.reset","earliest");
      cp.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");cp.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
      try(KafkaConsumer<String,String> consumer=new KafkaConsumer<>(cp)) {
        consumer.subscribe(List.of(allowed));Set<String> seen=new HashSet<>();long deadline=System.nanoTime()+Duration.ofSeconds(60).toNanos();
        while(seen.size()<6 && System.nanoTime()<deadline)for(ConsumerRecord<String,String> r:consumer.poll(Duration.ofMillis(300))) {
          int id=Math.toIntExact(r.offset()*3+r.partition());check(id>=start && id<start+6 && r.value().equals(user+"-scram-"+id) && seen.add(r.value()),"Authenticated replay mismatch");}
        check(seen.size()==6,"Incomplete SCRAM consumption");consumer.commitSync(Duration.ofSeconds(15));
        Map<TopicPartition,OffsetAndMetadata> committed=admin.listConsumerGroupOffsets(group).partitionsToOffsetAndMetadata().get(18,TimeUnit.SECONDS);
        for(int i=0;i<3;i++)check(committed.get(new TopicPartition(allowed,i))!=null && committed.get(new TopicPartition(allowed,i)).offset()==(start+6)/3,"Wrong committed next offset");
        System.out.println("OBS:SASL_COMMITTED_OFFSETS:"+committed);
      }
      pass("deterministic_records_acks_all_consumption_commits_and_resume");
    }
  }
}
