import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.config.ConfigResource;

/** Real keyed updates/null tombstones; offset snapshots tolerate compaction gaps. */
public class CompactionAcceptance {
  static final String BOOT="qa-kafka-ha-kafka-bootstrap:9092";
  static final Duration API=Duration.ofSeconds(20);
  static void check(boolean ok,String detail) {if(!ok)throw new IllegalStateException(detail);}
  static String phase;
  static void pass(String name) {System.out.println("CHECK:"+phase+"_"+name+":PASS");}
  static Properties base() {
    Properties p=new Properties();p.put("bootstrap.servers",BOOT);p.put("default.api.timeout.ms","20000");p.put("request.timeout.ms","10000");return p;
  }
  static int partition(String key) {
    switch(key) {case "customer-1":return 0;case "customer-2":return 1;case "customer-3":case "literal-null":return 2;default:throw new IllegalStateException("Unexpected key: "+key);}
  }
  static void send(KafkaProducer<String,String> p,String topic,String key,String value) throws Exception {
    RecordMetadata m=p.send(new ProducerRecord<>(topic,partition(key),key,value)).get(35,TimeUnit.SECONDS);
    check(m.partition()==partition(key),"Key routing changed");
  }
  static void health(Admin admin,String topic) throws Exception {
    TopicDescription td=admin.describeTopics(List.of(topic)).allTopicNames().get(25,TimeUnit.SECONDS).get(topic);
    check(td.partitions().size()==3,"Expected three partitions");
    for(TopicPartitionInfo part:td.partitions())check(part.leader()!=null && part.leader().id()>=0 && part.replicas().size()==3 && part.isr().size()==3,"Degraded topic replica metadata");
    ConfigResource cr=new ConfigResource(ConfigResource.Type.TOPIC,topic);
    Config actual=admin.describeConfigs(List.of(cr)).all().get(25,TimeUnit.SECONDS).get(cr);
    Map<String,String> expected=Map.of("cleanup.policy","compact","min.insync.replicas","2",
      "delete.retention.ms","86400000","min.cleanable.dirty.ratio","0.1","min.compaction.lag.ms","0",
      "segment.bytes","1048576","segment.ms","60000");
    for(Map.Entry<String,String> e:expected.entrySet()) {
      check(actual.get(e.getKey())!=null && actual.get(e.getKey()).value().equals(e.getValue()),"Config mismatch: "+e.getKey());
      System.out.println("OBS:CONFIG:"+e.getKey()+"="+actual.get(e.getKey()).value());
    }
  }
  static int snapshot(String topic,String tag) {
    Properties p=base();p.put("group.id",tag+"-snapshot-"+UUID.randomUUID());p.put("enable.auto.commit","false");
    p.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
    p.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
    try(KafkaConsumer<String,String> c=new KafkaConsumer<>(p)) {
      List<TopicPartition> parts=List.of(new TopicPartition(topic,0),new TopicPartition(topic,1),new TopicPartition(topic,2));
      c.assign(parts);c.seekToBeginning(parts);
      Map<TopicPartition,Long> ends=c.endOffsets(parts,API), starts=c.beginningOffsets(parts,API);
      for(TopicPartition tp:parts)check(ends.get(tp)==36,"Acknowledged log end changed: "+ends);
      Map<String,String> state=new TreeMap<>();Map<Integer,Long> last=new HashMap<>();
      int records=0,tombstones=0;boolean done=false;
      long deadline=System.nanoTime()+Duration.ofSeconds(50).toNanos();
      while(System.nanoTime()<deadline) {
        done=true;for(TopicPartition tp:parts)if(c.position(tp,API)<ends.get(tp))done=false;
        if(done)break;
        for(ConsumerRecord<String,String> record:c.poll(Duration.ofMillis(300))) {
          check(record.key()!=null && record.partition()==partition(record.key()),"Null key or changed routing");
          check(record.offset()>last.getOrDefault(record.partition(),-1L),"Offsets must advance, allowing gaps");
          last.put(record.partition(),record.offset());records++;
          if(record.value()==null) {state.remove(record.key());tombstones++;} else state.put(record.key(),record.value());
        }
      }
      check(done,"Bootstrap did not reach captured end offsets");
      check(state.equals(Map.of("customer-1","tier=diamond","customer-3","tier=premium","literal-null","null")),"Wrong rebuilt state: "+state);
      check(tombstones>=1,"No actual null-value tombstone observed");
      try {
        byte[] digest=java.security.MessageDigest.getInstance("SHA-256").digest(state.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
        System.out.println("OBS:STATE_CHECKSUM:"+HexFormat.of().formatHex(digest));
      } catch(java.security.NoSuchAlgorithmException e) {throw new IllegalStateException(e);}
      System.out.println("OBS:STATE:"+state+":records="+records+":actual_null_tombstones="+tombstones);
      System.out.println("OBS:OFFSET_SNAPSHOT:earliest="+starts+":latest="+ends+":last_returned="+last);
      return records;
    }
  }
  public static void main(String[] args) throws Exception {
    String topic=args[0],tag=args[1];phase=args[2];
    try(Admin admin=Admin.create(base())) {
      health(admin,topic);pass("effective_compaction_rf3_isr3");
      if(phase.equals("seed")) {
        Properties pp=base();pp.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");
        pp.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");
        pp.put("acks","all");pp.put("enable.idempotence","true");pp.put("compression.type","none");
        pp.put("batch.size","0");pp.put("max.block.ms","20000");pp.put("delivery.timeout.ms","30000");
        try(KafkaProducer<String,String> p=new KafkaProducer<>(pp)) {
          send(p,topic,"customer-1","tier=bronze");send(p,topic,"customer-2","tier=silver");
          send(p,topic,"customer-1","tier=gold");send(p,topic,"customer-3","tier=basic");
          send(p,topic,"customer-2","tier=platinum");send(p,topic,"customer-1","tier=diamond");
          for(int i=0;i<32;i++)for(int key=1;key<=3;key++)send(p,topic,"customer-"+key,tag+"-history-"+i+"|"+"x".repeat(65536));
          send(p,topic,"customer-1","tier=diamond");send(p,topic,"customer-2","tier=platinum");send(p,topic,"customer-3","tier=basic");
          send(p,topic,"literal-null","null");send(p,topic,"customer-2",null);send(p,topic,"customer-3","tier=premium");
        }
        pass("108_keyed_updates_and_real_null_tombstone_acknowledged");
      }
      int visible=snapshot(topic,tag);
      pass("exact_empty_store_rebuild_to_captured_end");pass("null_tombstone_distinct_from_literal_string");
      if(phase.equals("seed")) {
        long deadline=System.nanoTime()+Duration.ofSeconds(120).toNanos();
        while(visible==108 && System.nanoTime()<deadline) {Thread.sleep(3000);visible=snapshot(topic,tag);}
        System.out.println("OBS:CLEANER_PROGRESS:"+(visible<108?"OBSERVED":"NOT_OBSERVED_WITHIN_BOUND")+":visible_records="+visible+":acknowledged_records=108");
        pass("cleaner_observation_recorded_without_completion_sla");
      }
      health(admin,topic);pass("final_full_isr_and_config_unchanged");
      if(phase.equals("serve")) {
        java.util.concurrent.atomic.AtomicBoolean stopping=new java.util.concurrent.atomic.AtomicBoolean();
        java.util.concurrent.CountDownLatch closed=new java.util.concurrent.CountDownLatch(1);
        Thread hook=new Thread(() -> {stopping.set(true);try {closed.await(20,TimeUnit.SECONDS);} catch(InterruptedException e) {Thread.currentThread().interrupt();}});
        Runtime.getRuntime().addShutdownHook(hook);
        java.nio.file.Files.writeString(java.nio.file.Path.of("/tmp/compaction-ready"),"bootstrapped");
        try {while(!stopping.get())Thread.sleep(250);} finally {
          System.out.println("GRACEFUL_CLOSE");closed.countDown();
          try {Runtime.getRuntime().removeShutdownHook(hook);} catch(IllegalStateException e) { /* JVM shutdown */ }
        }
      }
    }
  }
}
