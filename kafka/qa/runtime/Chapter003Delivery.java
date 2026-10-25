import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

public class Chapter003Delivery {
  static final String TOPIC="qa-ch003-delivery";
  static final String BOOT="qa-six-kafka-bootstrap:9092";
  static final String RUN="__RUN__";
  static void require(boolean value,String message) {
    if(!value) throw new IllegalStateException(message);
  }
  public static void main(String[] args) throws Exception {
    Properties producerConfig=new Properties();
    producerConfig.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG,BOOT);
    producerConfig.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,StringSerializer.class.getName());
    producerConfig.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG,StringSerializer.class.getName());
    producerConfig.put(ProducerConfig.ACKS_CONFIG,"all");
    producerConfig.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG,"true");
    producerConfig.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION,"5");
    producerConfig.put(ProducerConfig.RETRIES_CONFIG,Integer.toString(Integer.MAX_VALUE));
    producerConfig.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG,"120000");
    List<String> expected=new ArrayList<>();
    long firstOffset=-1;
    try(KafkaProducer<String,String> producer=new KafkaProducer<>(producerConfig)) {
      for(int i=0;i<5;i++) {
        String value=RUN+"-event-"+i;
        RecordMetadata metadata=producer.send(new ProducerRecord<>(TOPIC,0,RUN,value))
          .get(40,TimeUnit.SECONDS);
        require(metadata.partition()==0,"Unexpected producer partition");
        if(i==0) firstOffset=metadata.offset();
        expected.add(value);
      }
      producer.flush();
    }
    System.out.println("CHECK:acks_all_idempotent_producer:PASS");
    Properties consumerConfig=new Properties();
    consumerConfig.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG,BOOT);
    consumerConfig.put(ConsumerConfig.GROUP_ID_CONFIG,"ch003-"+RUN);
    consumerConfig.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,StringDeserializer.class.getName());
    consumerConfig.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,StringDeserializer.class.getName());
    consumerConfig.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG,"false");
    consumerConfig.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG,"earliest");
    TopicPartition partition=new TopicPartition(TOPIC,0);
    try(KafkaConsumer<String,String> consumer=new KafkaConsumer<>(consumerConfig)) {
      consumer.assign(Collections.singletonList(partition));
      consumer.seek(partition,firstOffset);
      List<String> actual=new ArrayList<>();
      long deadline=System.nanoTime()+Duration.ofSeconds(50).toNanos();
      while(actual.size()<5 && System.nanoTime()<deadline) {
        for(ConsumerRecord<String,String> record:consumer.poll(Duration.ofMillis(500))) {
          require(record.partition()==0,"Unexpected consumer partition");
          actual.add(record.value());
        }
      }
      require(actual.equals(expected),"Consumed values differ from producer acknowledgements: "+actual);
      System.out.println("CHECK:delivery_and_partition_order:PASS");
      long nextOffset=consumer.position(partition);
      consumer.commitSync(Collections.singletonMap(partition,new OffsetAndMetadata(nextOffset)));
      require(consumer.committed(Collections.singleton(partition)).get(partition).offset()==nextOffset,
              "Committed offset mismatch");
      System.out.println("CHECK:explicit_commit_sync:PASS");
    }
    try(KafkaConsumer<String,String> restarted=new KafkaConsumer<>(consumerConfig)) {
      restarted.assign(Collections.singletonList(partition));
      OffsetAndMetadata committed=restarted.committed(Collections.singleton(partition)).get(partition);
      require(committed!=null && committed.offset()==firstOffset+5,
              "Restart did not observe expected committed offset");
      System.out.println("CHECK:restart_reads_committed_offset:PASS");
    }
    System.out.println("CH003_DELIVERY_OK");
  }
}
