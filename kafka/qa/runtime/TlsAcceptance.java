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
import javax.naming.ldap.*;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.errors.*;

/** mTLS identity stays in mounted Secrets; only public certificate metadata is emitted. */
public class TlsAcceptance {
  static final Path TRUST=Path.of("/trust/ca.crt"), STORE=Path.of("/identity/user.p12"), PASSWORD=Path.of("/identity/user.password");
  static String bootstrap,phase;
  static void check(boolean ok,String message) {if(!ok)throw new IllegalStateException(message);}
  static void pass(String name) {System.out.println("CHECK:"+phase+"_"+name+":PASS");}
  static KeyStore identity() throws Exception {
    KeyStore store=KeyStore.getInstance("PKCS12");char[] password=Files.readString(PASSWORD).trim().toCharArray();
    try(InputStream input=Files.newInputStream(STORE)) {store.load(input,password);} finally {Arrays.fill(password,'\0');}
    return store;
  }
  static SSLContext context(boolean trustLab,boolean clientIdentity) throws Exception {
    TrustManagerFactory tmf=TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
    if(trustLab) {
      KeyStore trust=KeyStore.getInstance(KeyStore.getDefaultType());trust.load(null,null);
      try(InputStream input=Files.newInputStream(TRUST)) {
        int i=0;for(java.security.cert.Certificate cert:CertificateFactory.getInstance("X.509").generateCertificates(input))trust.setCertificateEntry("ca-"+i++,cert);
      }
      tmf.init(trust);
    } else tmf.init((KeyStore)null);
    KeyManager[] managers=null;
    if(clientIdentity) {
      KeyManagerFactory kmf=KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());char[] password=Files.readString(PASSWORD).trim().toCharArray();
      try {kmf.init(identity(),password);managers=kmf.getKeyManagers();} finally {Arrays.fill(password,'\0');}
    }
    SSLContext context=SSLContext.getInstance("TLS");context.init(managers,tmf.getTrustManagers(),new SecureRandom());return context;
  }
  static String fingerprint(X509Certificate certificate) throws Exception {
    return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(certificate.getEncoded()));
  }
  static void metadata(String purpose,X509Certificate certificate) throws Exception {
    certificate.checkValidity();
    System.out.println("OBS:CERT:"+purpose+":subject="+certificate.getSubjectX500Principal()+":issuer="+certificate.getIssuerX500Principal()
      +":serial="+certificate.getSerialNumber().toString(16)+":notBefore="+certificate.getNotBefore().toInstant()+":notAfter="+certificate.getNotAfter().toInstant()+":sha256="+fingerprint(certificate));
  }
  static InetAddress address(String host) throws Exception {
    ExecutorService executor=Executors.newSingleThreadExecutor(r->{Thread t=new Thread(r,"tls-dns");t.setDaemon(true);return t;});
    try {return executor.submit(()->InetAddress.getByName(host)).get(10,TimeUnit.SECONDS);} finally {executor.shutdownNow();}
  }
  static void handshake(SSLContext context,String host,int port,String peerHost,boolean emit) throws Exception {
    Socket connected=new Socket();connected.connect(new InetSocketAddress(address(host),port),5000);connected.setSoTimeout(5000);
    try(SSLSocket socket=(SSLSocket)context.getSocketFactory().createSocket(connected,peerHost,port,true)) {
      socket.setSoTimeout(5000);SSLParameters parameters=socket.getSSLParameters();
      parameters.setEndpointIdentificationAlgorithm("HTTPS");parameters.setServerNames(List.of(new SNIHostName(peerHost)));socket.setSSLParameters(parameters);socket.startHandshake();
      if(emit) {
        X509Certificate leaf=(X509Certificate)socket.getSession().getPeerCertificates()[0];metadata("server-"+host,leaf);
        check(socket.getSession().getLocalPrincipal()!=null,"mTLS client principal missing");
        System.out.println("OBS:TLS_ENDPOINT:"+host+":"+port+":protocol="+socket.getSession().getProtocol()+":local_principal="+socket.getSession().getLocalPrincipal());
      }
    } finally {if(!connected.isClosed())connected.close();}
  }
  static Properties properties(boolean withIdentity) throws Exception {
    Properties p=new Properties();p.put("bootstrap.servers",bootstrap);p.put("default.api.timeout.ms","15000");p.put("request.timeout.ms","8000");
    p.put("security.protocol","SSL");p.put("ssl.endpoint.identification.algorithm","https");
    p.put("ssl.truststore.type","PEM");p.put("ssl.truststore.certificates",Files.readString(TRUST));
    if(withIdentity) {p.put("ssl.keystore.type","PKCS12");p.put("ssl.keystore.location",STORE.toString());p.put("ssl.keystore.password",Files.readString(PASSWORD).trim());}
    return p;
  }
  public static void main(String[] args) throws Exception {
    bootstrap=args[0];String allowed=args[1],denied=args[2],group=args[3],user=args[4];phase=args[5];int start=Integer.parseInt(args[6]);
    for(Path path:List.of(STORE,PASSWORD)) {
      Set<PosixFilePermission> permissions=Files.getPosixFilePermissions(path);
      check(!permissions.contains(PosixFilePermission.OTHERS_READ) && !permissions.contains(PosixFilePermission.OTHERS_WRITE),"Private identity files must not be world accessible");
    }
    KeyStore store=identity();X509Certificate client=null;
    for(String alias:Collections.list(store.aliases()))if(store.isKeyEntry(alias))client=(X509Certificate)store.getCertificate(alias);
    check(client!=null,"Client certificate absent");metadata("client",client);
    boolean cnMatches=false;for(Rdn rdn:new LdapName(client.getSubjectX500Principal().getName()).getRdns())if(rdn.getType().equalsIgnoreCase("CN") && user.equals(rdn.getValue().toString()))cnMatches=true;
    check(cnMatches,"Client certificate CN does not bind expected KafkaUser");
    try(InputStream input=Files.newInputStream(TRUST)) {for(java.security.cert.Certificate ca:CertificateFactory.getInstance("X.509").generateCertificates(input))metadata("cluster-ca",(X509Certificate)ca);}
    pass("safe_valid_certificate_metadata_and_identity_binding");
    URI endpoint=URI.create("ssl://"+bootstrap);String host=endpoint.getHost();int port=endpoint.getPort();
    SSLContext good=context(true,true);handshake(good,host,port,host,true);
    try(Admin admin=Admin.create(properties(true))) {
      Collection<Node> nodes=admin.describeCluster().nodes().get(18,TimeUnit.SECONDS);check(nodes.size()==3,"Expected three brokers");
      for(Node node:nodes) {check(node.port()==port,"Advertised endpoint is not TLS listener");handshake(good,node.host(),node.port(),node.host(),true);
        Properties direct=properties(true);direct.put("bootstrap.servers",node.host()+":"+node.port());
        try(Admin one=Admin.create(direct)) {check(one.describeCluster().nodes().get(18,TimeUnit.SECONDS).size()==3,"Direct TLS broker metadata failed");}}
      pass("bootstrap_and_all_brokers_chain_san_mtls_metadata");
      boolean wrongCa=false;try {handshake(context(false,true),host,port,host,false);} catch(SSLException expected) {wrongCa=true;System.out.println("OBS:TLS_NEGATIVE:UNTRUSTED_CA:"+expected.getClass().getSimpleName());}
      check(wrongCa,"Wrong trust bundle unexpectedly succeeded");pass("untrusted_ca_rejected");
      boolean wrongName=false;try {handshake(good,host,port,"wrong-ch027.invalid",false);} catch(SSLException expected) {wrongName=true;System.out.println("OBS:TLS_NEGATIVE:HOSTNAME_MISMATCH:"+expected.getClass().getSimpleName());}
      check(wrongName,"Wrong peer hostname unexpectedly succeeded");pass("wrong_hostname_rejected_with_verification_enabled");
      Admin anonymous=Admin.create(properties(false));boolean noIdentity=false;
      try {anonymous.describeCluster().nodes().get(18,TimeUnit.SECONDS);}
      catch(ExecutionException expected) {check(expected.getCause() instanceof SslAuthenticationException,"Missing identity produced an ambiguous non-TLS-authentication failure");noIdentity=true;System.out.println("OBS:TLS_NEGATIVE:NO_CLIENT_CERT:SslAuthenticationException");}
      finally {anonymous.close(Duration.ofSeconds(1));}
      check(noIdentity,"mTLS listener accepted a client without identity");pass("missing_client_certificate_authentication_rejected");
      TopicDescription topic=admin.describeTopics(List.of(allowed)).allTopicNames().get(18,TimeUnit.SECONDS).get(allowed);
      check(topic.partitions().size()==3,"Expected three partitions");for(TopicPartitionInfo part:topic.partitions())check(part.leader()!=null && part.leader().id()>=0 && part.replicas().size()==3 && part.isr().size()==3,"Degraded RF/ISR");
      Properties p=properties(true);p.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");p.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");p.put("acks","all");p.put("enable.idempotence","true");p.put("max.block.ms","15000");p.put("delivery.timeout.ms","30000");
      try(KafkaProducer<String,String> negative=new KafkaProducer<>(p)) {
        boolean aclDenied=false;try {negative.send(new ProducerRecord<>(denied,0,"key","must-not-be-written")).get(20,TimeUnit.SECONDS);}
        catch(ExecutionException expected) {check(expected.getCause() instanceof TopicAuthorizationException,"Denied topic produced a non-authorization failure");aclDenied=true;}
        check(aclDenied,"Principal unexpectedly wrote outside literal topic ACL");pass("valid_identity_denied_unapproved_topic");
      }
      try(KafkaProducer<String,String> producer=new KafkaProducer<>(p)) {
        for(int i=start;i<start+6;i++) {RecordMetadata m=producer.send(new ProducerRecord<>(allowed,i%3,"key-"+(i%3),user+"-tls-"+i)).get(35,TimeUnit.SECONDS);check(m.offset()==i/3,"Unexpected acknowledged TLS offset");}
      }
      Properties cp=properties(true);cp.put("group.id",group);cp.put("enable.auto.commit","false");cp.put("auto.offset.reset","earliest");
      cp.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");cp.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
      try(KafkaConsumer<String,String> consumer=new KafkaConsumer<>(cp)) {
        consumer.subscribe(List.of(allowed));Set<String> seen=new HashSet<>();long deadline=System.nanoTime()+Duration.ofSeconds(60).toNanos();
        while(seen.size()<6 && System.nanoTime()<deadline)for(ConsumerRecord<String,String> record:consumer.poll(Duration.ofMillis(300))) {
          int id=Math.toIntExact(record.offset()*3+record.partition());check(id>=start && id<start+6 && record.value().equals(user+"-tls-"+id) && seen.add(record.value()),"TLS event/resume mismatch");}
        check(seen.size()==6,"Incomplete authenticated TLS consumption");consumer.commitSync(Duration.ofSeconds(15));
        Map<TopicPartition,OffsetAndMetadata> committed=admin.listConsumerGroupOffsets(group).partitionsToOffsetAndMetadata().get(18,TimeUnit.SECONDS);
        for(int i=0;i<3;i++)check(committed.containsKey(new TopicPartition(allowed,i)) && committed.get(new TopicPartition(allowed,i)).offset()==(start+6)/3,"Wrong committed TLS next offset");
        System.out.println("OBS:TLS_COMMITTED_OFFSETS:"+committed);
      }
      pass("authorized_tls_acks_all_records_offsets_and_resume");
    }
  }
}
