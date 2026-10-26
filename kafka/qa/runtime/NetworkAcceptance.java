import java.net.*;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;

/** Bounded client-side network probes; never changes broker listeners or policies. */
public class NetworkAcceptance {
  static final String HOST="qa-kafka-ha-kafka-bootstrap", BOOT=HOST+":9092";
  static void check(boolean ok,String message) {if(!ok)throw new IllegalStateException(message);}
  static void pass(String name) {System.out.println("CHECK:"+name+":PASS");}
  static Properties base(String bootstrap) {
    Properties p=new Properties();p.put("bootstrap.servers",bootstrap);p.put("default.api.timeout.ms","10000");p.put("request.timeout.ms","5000");return p;
  }
  static InetAddress[] lookup(String host) throws Exception {
    ExecutorService executor=Executors.newSingleThreadExecutor(r->{Thread t=new Thread(r,"bounded-dns");t.setDaemon(true);return t;});
    try {
      try{return executor.submit(()->InetAddress.getAllByName(host)).get(10,TimeUnit.SECONDS);}
      catch(ExecutionException e) {if(e.getCause() instanceof Exception)throw (Exception)e.getCause();throw e;}
    } finally {executor.shutdownNow();}
  }
  public static void main(String[] args) throws Exception {
    String topic=args[0],tag=args[1];int wrongPort=Integer.parseInt(args[2]);
    System.out.println("OBS:RESOLV_CONF:"+Files.readString(Path.of("/etc/resolv.conf")).replace('\n',';'));
    InetAddress[] bootstrap=lookup(HOST);
    check(bootstrap.length>0,"Bootstrap DNS has no addresses");
    System.out.println("OBS:BOOTSTRAP_DNS:"+String.join(",",Arrays.stream(bootstrap).map(InetAddress::getHostAddress).toList()));
    pass("bootstrap_dns_and_resolver_observed");
    try(Admin admin=Admin.create(base(BOOT))) {
      String cluster=admin.describeCluster().clusterId().get(12,TimeUnit.SECONDS);
      Collection<Node> nodes=admin.describeCluster().nodes().get(12,TimeUnit.SECONDS);
      check(nodes.size()==3,"Expected three advertised brokers");
      for(Node node:nodes) {
        InetAddress[] resolved=lookup(node.host());
        long started=System.nanoTime();
        try(Socket socket=new Socket()) {socket.connect(new InetSocketAddress(resolved[0],node.port()),3000);}
        System.out.println("OBS:TCP_CONNECT_MS:"+node.id()+":"+(System.nanoTime()-started)/1000000.0);
        try(Admin direct=Admin.create(base(node.host()+":"+node.port()))) {
          check(cluster.equals(direct.describeCluster().clusterId().get(12,TimeUnit.SECONDS)),"Advertised endpoint returns another cluster");
        }
        System.out.println("OBS:BROKER_ENDPOINT:"+node.id()+"|"+node.host()+"|"+node.port()+"|"+String.join(",",Arrays.stream(resolved).map(InetAddress::getHostAddress).toList()));
      }
      pass("all_advertised_broker_dns_tcp_and_kafka_metadata");
      TopicDescription td=admin.describeTopics(List.of(topic)).allTopicNames().get(12,TimeUnit.SECONDS).get(topic);
      check(td.partitions().size()==3,"Expected three partitions");
      for(TopicPartitionInfo partition:td.partitions())check(partition.leader()!=null && partition.leader().id()>=0 && partition.replicas().size()==3 && partition.isr().size()==3,"Unhealthy RF/ISR");
      pass("topic_leaders_rf3_full_isr");
      boolean dnsFailed=false;
      try {lookup("nonexistent-ch026.invalid");} catch(UnknownHostException|java.util.concurrent.TimeoutException expected) {dnsFailed=true;System.out.println("OBS:NEGATIVE_DNS:"+expected.getClass().getSimpleName());}
      check(dnsFailed,"Reserved invalid hostname unexpectedly resolved");pass("invalid_dns_classified_without_cluster_change");
      boolean tcpFailed=false;
      try(Socket socket=new Socket()) {socket.connect(new InetSocketAddress(bootstrap[0],wrongPort),2000);}
      catch(ConnectException|SocketTimeoutException|NoRouteToHostException expected) {tcpFailed=true;System.out.println("OBS:NEGATIVE_TCP:"+expected.getClass().getSimpleName());}
      check(tcpFailed,"Verified-unused Service port unexpectedly accepted a connection");
      Properties bad=base(HOST+":"+wrongPort);bad.put("default.api.timeout.ms","3000");bad.put("request.timeout.ms","1000");
      Admin wrong=Admin.create(bad);boolean metadataFailed=false;
      try {wrong.describeCluster().nodes().get(5,TimeUnit.SECONDS);}
      catch(ExecutionException expected) {check(expected.getCause() instanceof org.apache.kafka.common.errors.TimeoutException,"Wrong port produced unexpected non-connectivity failure: "+expected.getCause());metadataFailed=true;}
      catch(java.util.concurrent.TimeoutException expected) {metadataFailed=true;}
      finally {wrong.close(Duration.ofSeconds(1));}
      check(metadataFailed,"Kafka metadata unexpectedly succeeded on unused port");
      pass("unused_port_dns_valid_tcp_and_metadata_failure_classified");
      Properties pp=base(BOOT);pp.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");pp.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");
      pp.put("acks","all");pp.put("enable.idempotence","true");pp.put("max.block.ms","15000");pp.put("delivery.timeout.ms","20000");
      try(KafkaProducer<String,String> producer=new KafkaProducer<>(pp)) {
        for(int i=0;i<6;i++)producer.send(new ProducerRecord<>(topic,i%3,"key-"+(i%3),tag+"-net-"+i)).get(25,TimeUnit.SECONDS);
      }
      Properties cp=base(BOOT);cp.put("group.id",tag+"-audit");cp.put("enable.auto.commit","false");
      cp.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");cp.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
      try(KafkaConsumer<String,String> consumer=new KafkaConsumer<>(cp)) {
        List<TopicPartition> parts=List.of(new TopicPartition(topic,0),new TopicPartition(topic,1),new TopicPartition(topic,2));
        consumer.assign(parts);consumer.seekToBeginning(parts);Set<String> seen=new HashSet<>();long deadline=System.nanoTime()+Duration.ofSeconds(40).toNanos();
        while(seen.size()<6 && System.nanoTime()<deadline)for(ConsumerRecord<String,String> r:consumer.poll(Duration.ofMillis(300))) {
          int id=Math.toIntExact(r.offset()*3+r.partition());check(id<6 && r.value().equals(tag+"-net-"+id) && seen.add(r.value()),"Network payload reconciliation failed");
        }
        check(seen.size()==6,"Missing network ledger records");
        for(long end:consumer.endOffsets(parts,Duration.ofSeconds(10)).values())check(end==2,"Unexpected record count");
      }
      pass("six_acknowledged_records_reconciled_after_negative_probes");
      check(cluster.equals(admin.describeCluster().clusterId().get(12,TimeUnit.SECONDS)),"Cluster changed after client probes");
      pass("positive_kafka_metadata_recovers_after_negative_probes");
    }
  }
}
