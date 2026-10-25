import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.serialization.*;

public class Chapter003Retry {
  static final String BOOT="qa-six-kafka-bootstrap:9092";
  static final String TOPIC="qa-ch003-delivery";
  static final String RUN="__RUN__";
  static void check(boolean value,String message) { if(!value) throw new IllegalStateException(message); }
  static Properties producerConfig() {
    Properties p=new Properties();
    p.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG,BOOT);
    p.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,StringSerializer.class.getName());
    p.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG,StringSerializer.class.getName());
    p.put(ProducerConfig.ACKS_CONFIG,"all");
    p.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG,"true");
    p.put(ProducerConfig.RETRIES_CONFIG,Integer.toString(Integer.MAX_VALUE));
    p.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION,"5");
    p.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG,"180000");
    p.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG,"15000");
    return p;
  }
  static List<String> consume(long start,int count) {
    Properties p=new Properties();
    p.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG,BOOT);
    p.put(ConsumerConfig.GROUP_ID_CONFIG,"ch003-retry-"+RUN);
    p.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,StringDeserializer.class.getName());
    p.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,StringDeserializer.class.getName());
    p.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG,"false");
    TopicPartition tp=new TopicPartition(TOPIC,0);
    List<String> seen=new ArrayList<>();
    try(KafkaConsumer<String,String> c=new KafkaConsumer<>(p)) {
      c.assign(Collections.singletonList(tp));
      c.seek(tp,start);
      long deadline=System.nanoTime()+Duration.ofSeconds(90).toNanos();
      while(seen.size()<count && System.nanoTime()<deadline) {
        for(ConsumerRecord<String,String> r:c.poll(Duration.ofMillis(500))) seen.add(r.value());
      }
      // Ensure no unexpected extra records in the tested offset range.
      long end=c.endOffsets(Collections.singleton(tp)).get(tp);
      check(end-start==count,"Unexpected log length: expected "+count+" got "+(end-start));
    }
    return seen;
  }
  public static void main(String[] args) throws Exception {
    List<String> expected=new ArrayList<>();
    long start=-1;
    try(KafkaProducer<String,String> producer=new KafkaProducer<>(producerConfig())) {
      for(int i=0;i<12;i++) {
        String value=RUN+"-retry-"+i;
        RecordMetadata m=producer.send(new ProducerRecord<>(TOPIC,0,RUN,value)).get(150,TimeUnit.SECONDS);
        if(i==0) start=m.offset();
        expected.add(value);
        if(i==5) System.out.println("MIDPOINT_READY");
      }
      producer.flush();
    }
    System.out.println("CHECK:acknowledged_writes:PASS");
    List<String> actual=consume(start,12);
    check(actual.equals(expected),"Duplicate, missing, or out-of-order records: "+actual);
    System.out.println("CHECK:no_duplicate_records_in_test_window:PASS");
    System.out.println("CHECK:partition_order_preserved:PASS");
    System.out.println("RETRY_ACCEPTANCE_OK");
  }
}
