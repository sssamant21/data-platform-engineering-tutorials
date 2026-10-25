import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.config.ConfigResource;

/** Bounded deterministic storage workload; no broker filesystem writes by this client. */
public class StorageAcceptance {
  static final String BOOT="qa-kafka-ha-kafka-bootstrap:9092";
  static final int COUNT=96, PAYLOAD_BYTES=65536;
  static final Duration API=Duration.ofSeconds(20);
  static void require(boolean ok,String detail) {if(!ok)throw new IllegalStateException(detail);}
  static void pass(String name) {System.out.println("CHECK:"+name+":PASS");}
  static Properties base() {
    Properties p=new Properties();p.put("bootstrap.servers",BOOT);
    p.put("default.api.timeout.ms","20000");p.put("request.timeout.ms","10000");return p;
  }
  static void health(Admin admin,String topic) throws Exception {
    TopicDescription td=admin.describeTopics(List.of(topic)).allTopicNames().get(25,TimeUnit.SECONDS).get(topic);
    require(td.partitions().size()==3,"Expected three partitions");
    for(TopicPartitionInfo part:td.partitions())
      require(part.leader()!=null && part.leader().id()>=0 && part.replicas().size()==3 && part.isr().size()==3,
              "Degraded replica metadata: "+part);
    ConfigResource cr=new ConfigResource(ConfigResource.Type.TOPIC,topic);
    Config effective=admin.describeConfigs(List.of(cr)).all().get(25,TimeUnit.SECONDS).get(cr);
    Map<String,String> expected=Map.of("cleanup.policy","delete","retention.ms","3600000",
      "retention.bytes","16777216","segment.bytes","1048576","segment.ms","60000","min.insync.replicas","2");
    for(Map.Entry<String,String> entry:expected.entrySet()) {
      ConfigEntry actual=effective.get(entry.getKey());
      require(actual!=null && actual.value().equals(entry.getValue()),"Effective config mismatch: "+entry.getKey());
      System.out.println("OBS:CONFIG:"+entry.getKey()+"="+actual.value());
    }
  }
  public static void main(String[] args) throws Exception {
    String topic=args[0], tag=args[1];
    try(Admin admin=Admin.create(base())) {
      health(admin,topic);pass("effective_retention_segment_and_durability_config");
      for(Node node:admin.describeCluster().nodes().get(25,TimeUnit.SECONDS))
        System.out.println("OBS:NODE:"+node.id()+":"+node.host());
      Properties pp=base();pp.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");
      pp.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");
      pp.put("acks","all");pp.put("enable.idempotence","true");pp.put("compression.type","none");
      pp.put("batch.size","0");pp.put("max.block.ms","20000");pp.put("delivery.timeout.ms","30000");
      List<String> expected=new ArrayList<>();
      try(KafkaProducer<String,String> producer=new KafkaProducer<>(pp)) {
        for(int i=0;i<COUNT;i++) {
          String value=tag+"-event-"+String.format("%03d",i)+"|"+"x".repeat(PAYLOAD_BYTES);
          RecordMetadata meta=producer.send(new ProducerRecord<>(topic,i%3,"key-"+(i%3),value)).get(35,TimeUnit.SECONDS);
          require(meta.partition()==i%3 && meta.offset()==i/3,"Unexpected acknowledged offset: "+meta.offset());
          expected.add(value);
        }
      }
      System.out.println("OBS:acknowledged_records:"+COUNT+":payload_bytes_per_record:"+PAYLOAD_BYTES);
      pass("96_idempotent_acks_all_records_acknowledged");
      Properties cp=base();cp.put("group.id",tag+"-audit");cp.put("enable.auto.commit","false");
      cp.put("auto.offset.reset","earliest");
      cp.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
      cp.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
      try(KafkaConsumer<String,String> consumer=new KafkaConsumer<>(cp)) {
        List<TopicPartition> parts=List.of(new TopicPartition(topic,0),new TopicPartition(topic,1),new TopicPartition(topic,2));
        consumer.assign(parts);consumer.seekToBeginning(parts);
        Set<String> seen=new HashSet<>();Map<Integer,Long> next=new HashMap<>();
        long until=System.nanoTime()+Duration.ofSeconds(60).toNanos();
        while(seen.size()<COUNT && System.nanoTime()<until) {
          for(ConsumerRecord<String,String> record:consumer.poll(Duration.ofMillis(300))) {
            long offset=next.getOrDefault(record.partition(),0L);
            require(record.offset()==offset,"Per-partition sequence mismatch");
            int id=Math.toIntExact(record.offset()*3+record.partition());
            require(id<COUNT && record.value().equals(expected.get(id)),"Payload/event ID mismatch");
            require(seen.add(record.value()),"Duplicate event ID");
            next.put(record.partition(),offset+1);
          }
        }
        require(seen.size()==COUNT,"Incomplete event reconciliation: "+seen.size());
        Map<TopicPartition,Long> ends=consumer.endOffsets(parts,API), starts=consumer.beginningOffsets(parts,API);
        for(TopicPartition tp:parts)
          require(starts.get(tp)==0 && ends.get(tp)==32 && consumer.position(tp,API)==32,"Unexpected retained offset window: "+tp);
        System.out.println("OBS:retained_offset_window:"+starts+":"+ends);
      }
      pass("96_exact_payloads_and_partition_order_reconciled");
      pass("all_records_retained_during_bounded_test");
      health(admin,topic);pass("final_full_isr_and_config_unchanged");
    }
  }
}
