import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.config.ConfigResource;

/** Local-only baseline. Does not install a plugin, enable tiering or access a bucket. */
public class TieredPreflight {
  static final String BOOT="qa-kafka-ha-kafka-bootstrap:9092";
  static void check(boolean ok,String message) {if(!ok)throw new IllegalStateException(message);}
  static void pass(String name) {System.out.println("CHECK:"+name+":PASS");}
  static Properties base() {
    Properties p=new Properties();p.put("bootstrap.servers",BOOT);p.put("default.api.timeout.ms","20000");p.put("request.timeout.ms","10000");return p;
  }
  public static void main(String[] args) throws Exception {
    String topic=args[0],tag=args[1];
    try(Admin admin=Admin.create(base())) {
      Collection<Node> nodes=admin.describeCluster().nodes().get(25,TimeUnit.SECONDS);
      check(nodes.size()==3,"Expected three brokers");
      for(Node node:nodes) {
        ConfigResource broker=new ConfigResource(ConfigResource.Type.BROKER,Integer.toString(node.id()));
        Config config=admin.describeConfigs(List.of(broker)).all().get(25,TimeUnit.SECONDS).get(broker);
        ConfigEntry enabled=config.get("remote.log.storage.system.enable");
        check(enabled!=null && "false".equals(enabled.value()),"Remote feature unexpectedly enabled/unknown; stop isolated baseline");
        for(String name:List.of("remote.log.storage.system.enable","remote.log.storage.manager.class.name","remote.log.metadata.manager.class.name")) {
          ConfigEntry entry=config.get(name);
          System.out.println("OBS:BROKER_CONFIG:"+node.id()+":"+name+"="+(entry==null?"UNAVAILABLE":entry.value()));
        }
      }
      pass("all_brokers_remote_feature_disabled_no_toggles");
      TopicDescription td=admin.describeTopics(List.of(topic)).allTopicNames().get(25,TimeUnit.SECONDS).get(topic);
      check(td.partitions().size()==3,"Expected three partitions");
      for(TopicPartitionInfo part:td.partitions())check(part.leader()!=null && part.leader().id()>=0 && part.replicas().size()==3 && part.isr().size()==3,"Degraded RF/ISR");
      ConfigResource resource=new ConfigResource(ConfigResource.Type.TOPIC,topic);
      Config topicConfig=admin.describeConfigs(List.of(resource)).all().get(25,TimeUnit.SECONDS).get(resource);
      check(topicConfig.get("remote.storage.enable")!=null && "false".equals(topicConfig.get("remote.storage.enable").value()),"Topic remote storage unexpectedly enabled");
      check(topicConfig.get("min.insync.replicas").value().equals("2"),"min ISR mismatch");
      pass("local_baseline_topic_rf3_isr3_remote_disabled");
      Properties p=base();p.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");p.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");
      p.put("acks","all");p.put("enable.idempotence","true");p.put("max.block.ms","20000");p.put("delivery.timeout.ms","30000");
      try(KafkaProducer<String,String> producer=new KafkaProducer<>(p)) {
        for(int i=0;i<6;i++)producer.send(new ProducerRecord<>(topic,i%3,"key-"+(i%3),tag+"-local-"+i)).get(35,TimeUnit.SECONDS);
      }
      p=base();p.put("group.id",tag+"-local-audit");p.put("enable.auto.commit","false");
      p.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");p.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
      try(KafkaConsumer<String,String> c=new KafkaConsumer<>(p)) {
        List<TopicPartition> parts=List.of(new TopicPartition(topic,0),new TopicPartition(topic,1),new TopicPartition(topic,2));
        c.assign(parts);c.seekToBeginning(parts);Set<String> seen=new HashSet<>();
        long deadline=System.nanoTime()+Duration.ofSeconds(45).toNanos();
        while(seen.size()<6 && System.nanoTime()<deadline)for(ConsumerRecord<String,String> r:c.poll(Duration.ofMillis(300))) {
          int id=Math.toIntExact(r.offset()*3+r.partition());
          check(id<6 && r.value().equals(tag+"-local-"+id) && seen.add(r.value()),"Local baseline mismatch");
        }
        check(seen.size()==6,"Incomplete local baseline consumption");
        Map<TopicPartition,Long> ends=c.endOffsets(parts,Duration.ofSeconds(20));
        for(TopicPartition tp:parts)check(ends.get(tp)==2,"Unexpected local log end");
        System.out.println("OBS:LOCAL_ONLY_END_OFFSETS:"+ends);
      }
      pass("six_local_records_reconciled_not_remote_read_proof");
      System.out.println("OBS:CONDITIONAL_REMOTE_INTEGRATION:NOT_EXECUTED_NO_REVIEWED_PLUGIN_OR_BUCKET");
    }
  }
}
