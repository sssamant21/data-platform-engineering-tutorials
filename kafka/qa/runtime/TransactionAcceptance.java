import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.config.ConfigResource;
import org.apache.kafka.common.errors.ProducerFencedException;

/** Executed only in a disposable Kubernetes client Job with unique topics/IDs. */
public class TransactionAcceptance {
  static String input, output, group, tag;
  static final String BOOT="qa-kafka-ha-kafka-bootstrap:9092";
  static final Duration API=Duration.ofSeconds(20);
  static void check(boolean value,String message) {if(!value)throw new IllegalStateException(message);}
  static void pass(String name) {System.out.println("CHECK:"+name+":PASS");}
  static Properties base() {
    Properties p=new Properties();
    p.put("bootstrap.servers",BOOT);p.put("default.api.timeout.ms","20000");p.put("request.timeout.ms","10000");
    return p;
  }
  static KafkaProducer<String,String> producer(String id) {
    Properties p=base();
    p.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");
    p.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");
    p.put("acks","all");p.put("enable.idempotence","true");
    p.put("max.in.flight.requests.per.connection","5");p.put("max.block.ms","30000");
    p.put("delivery.timeout.ms","30000");
    if(id!=null) {p.put("transactional.id",id);p.put("transaction.timeout.ms","60000");}
    return new KafkaProducer<>(p);
  }
  static KafkaConsumer<String,String> consumer(String id,String isolation) {
    Properties p=base();p.put("group.id",id);p.put("enable.auto.commit","false");
    p.put("auto.offset.reset","earliest");p.put("isolation.level",isolation);p.put("group.protocol","classic");
    p.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
    p.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
    return new KafkaConsumer<>(p);
  }
  static List<TopicPartition> partitions(String topic) {
    return List.of(new TopicPartition(topic,0),new TopicPartition(topic,1),new TopicPartition(topic,2));
  }
  static List<String> snapshot(String topic,String isolation) {
    try(KafkaConsumer<String,String> c=consumer(tag+"-audit-"+UUID.randomUUID(),isolation)) {
      List<TopicPartition> parts=partitions(topic);c.assign(parts);c.seekToBeginning(parts);
      Map<TopicPartition,Long> end=c.endOffsets(parts,API);
      List<String> values=new ArrayList<>();long until=System.nanoTime()+Duration.ofSeconds(40).toNanos();
      while(System.nanoTime()<until) {
        boolean done=true;
        for(TopicPartition tp:parts) if(c.position(tp,API)<end.get(tp)) done=false;
        if(done) {System.out.println("OBS:"+isolation+":"+values);return values;}
        for(ConsumerRecord<String,String> r:c.poll(Duration.ofMillis(300))) values.add(r.value());
      }
      throw new IllegalStateException("Snapshot did not reach captured end offsets");
    }
  }
  static Map<TopicPartition,OffsetAndMetadata> committed(Admin admin) throws Exception {
    return admin.listConsumerGroupOffsets(group).partitionsToOffsetAndMetadata().get(25,TimeUnit.SECONDS);
  }
  static List<ConsumerRecord<String,String>> batch(KafkaConsumer<String,String> c) {
    List<ConsumerRecord<String,String>> records=new ArrayList<>();
    long end=System.nanoTime()+Duration.ofSeconds(50).toNanos();
    while(records.size()<6 && System.nanoTime()<end)
      for(ConsumerRecord<String,String> r:c.poll(Duration.ofMillis(300))) records.add(r);
    check(records.size()==6,"Expected six input records, got "+records.size());
    Set<String> unique=new HashSet<>();for(ConsumerRecord<String,String> r:records)unique.add(r.value());
    check(unique.size()==6,"Duplicate input IDs");return records;
  }
  static void write(KafkaProducer<String,String> p,String topic,int partition,String value) throws Exception {
    p.send(new ProducerRecord<>(topic,partition,"key-"+partition,value)).get(35,TimeUnit.SECONDS);
  }
  static Map<TopicPartition,OffsetAndMetadata> transform(KafkaProducer<String,String> p,List<ConsumerRecord<String,String>> records) throws Exception {
    Map<TopicPartition,OffsetAndMetadata> offsets=new HashMap<>();
    for(ConsumerRecord<String,String> r:records) {
      write(p,output,r.partition(),"processed-"+r.value());
      offsets.put(new TopicPartition(r.topic(),r.partition()),new OffsetAndMetadata(r.offset()+1));
    }
    return offsets;
  }
  static void health(Admin admin) throws Exception {
    Map<String,TopicDescription> descriptions=admin.describeTopics(List.of(input,output)).allTopicNames().get(25,TimeUnit.SECONDS);
    for(String topic:List.of(input,output)) {
      check(descriptions.get(topic).partitions().size()==3,"Expected three partitions");
      for(TopicPartitionInfo part:descriptions.get(topic).partitions())
        check(part.leader()!=null && part.leader().id()>=0 && part.replicas().size()==3 && part.isr().size()==3,"Degraded partition "+part);
      ConfigResource resource=new ConfigResource(ConfigResource.Type.TOPIC,topic);
      Config config=admin.describeConfigs(List.of(resource)).all().get(25,TimeUnit.SECONDS).get(resource);
      check(config.get("min.insync.replicas").value().equals("2"),"min ISR changed");
    }
  }
  public static void main(String[] args) throws Exception {
    input=args[0];output=args[1];group=args[2];tag=args[3];
    try(Admin admin=Admin.create(base())) {
      health(admin);pass("topics_rf3_isr3_minisr2");
      try(KafkaProducer<String,String> p=producer(tag+"-visibility")) {
        p.initTransactions();p.beginTransaction();write(p,output,0,"committed");p.commitTransaction();
        p.beginTransaction();write(p,output,0,"aborted");p.abortTransaction();
        check(snapshot(output,"read_committed").equals(List.of("committed")),"Committed visibility mismatch");
        check(snapshot(output,"read_uncommitted").equals(List.of("committed","aborted")),"Aborted record not observed by read_uncommitted");
        pass("commit_abort_isolation");
        p.beginTransaction();write(p,output,0,"open");
        try(KafkaProducer<String,String> normal=producer(null)) {write(normal,output,0,"behind-open");}
        check(snapshot(output,"read_committed").equals(List.of("committed")),"Read passed open transaction LSO");
        pass("open_transaction_blocks_read_committed");
        p.abortTransaction();
        check(snapshot(output,"read_committed").equals(List.of("committed","behind-open")),"LSO did not advance after abort");
        pass("abort_releases_last_stable_offset");
      }
      try(KafkaProducer<String,String> old=producer(tag+"-fencing");KafkaProducer<String,String> replacement=producer(tag+"-fencing")) {
        old.initTransactions();old.beginTransaction();write(old,output,0,"fenced");
        replacement.initTransactions();
        boolean fenced=false;
        try {old.commitTransaction();} catch(ProducerFencedException e) {fenced=true;}
        check(fenced,"Old producer was not fenced");
        replacement.beginTransaction();write(replacement,output,0,"replacement");replacement.commitTransaction();
      }
      check(snapshot(output,"read_committed").equals(List.of("committed","behind-open","replacement")),"Fenced output leaked");
      pass("old_producer_fenced_new_owner_commits");
      try(KafkaProducer<String,String> seed=producer(null)) {
        for(int i=0;i<6;i++)write(seed,input,i%3,tag+"-event-"+i);
      }
      pass("six_durable_input_events");
      try(KafkaConsumer<String,String> c=consumer(group,"read_committed");KafkaProducer<String,String> p=producer(tag+"-processor")) {
        c.subscribe(List.of(input));List<ConsumerRecord<String,String>> records=batch(c);
        p.initTransactions();p.beginTransaction();
        Map<TopicPartition,OffsetAndMetadata> offsets=transform(p,records);
        p.sendOffsetsToTransaction(offsets,c.groupMetadata());p.abortTransaction();
        check(committed(admin).isEmpty(),"Aborted transaction advanced group offsets");
        check(snapshot(output,"read_committed").size()==3,"Aborted transform output visible");
        pass("aborted_output_and_offsets_unchanged");
        for(TopicPartition tp:c.assignment())c.seek(tp,0);
        records=batch(c);p.beginTransaction();offsets=transform(p,records);
        p.sendOffsetsToTransaction(offsets,c.groupMetadata());p.commitTransaction();
        Map<TopicPartition,OffsetAndMetadata> observed=committed(admin);
        check(observed.size()==3,"Missing committed partitions");
        for(TopicPartition tp:partitions(input))check(observed.get(tp).offset()==2,"Wrong committed next offset");
        System.out.println("OBS:committed-input-offsets:"+observed);pass("atomic_output_and_offsets_committed");
      }
      List<String> actual=snapshot(output,"read_committed");
      List<String> expected=new ArrayList<>(List.of("committed","behind-open","replacement"));
      for(int i=0;i<6;i++)expected.add("processed-"+tag+"-event-"+i);
      Collections.sort(actual);Collections.sort(expected);check(actual.equals(expected),"Output ID reconciliation mismatch");
      pass("exact_output_id_reconciliation");
      try(KafkaConsumer<String,String> restart=consumer(group,"read_committed")) {
        restart.assign(partitions(input));
        for(TopicPartition tp:partitions(input)) check(restart.position(tp,API)==2,"Restart did not resume committed next offset");
        check(restart.poll(Duration.ofSeconds(2)).isEmpty(),"Restart replayed committed input");
      }
      pass("restart_resumes_transactional_offsets");health(admin);pass("final_full_isr");
    }
  }
}
