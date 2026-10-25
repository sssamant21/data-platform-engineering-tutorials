import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.metrics.Metric;
import org.apache.kafka.common.serialization.*;

public class Chapter003LeaderFailover {
  static final String BOOT="qa-six-kafka-bootstrap:9092", TOPIC="qa-ch003-delivery", RUN="__RUN__";
  static void check(boolean x,String m){if(!x)throw new IllegalStateException(m);}
  public static void main(String[] args)throws Exception {
    Properties p=new Properties();
    p.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG,BOOT);
    p.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,StringSerializer.class.getName());
    p.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG,StringSerializer.class.getName());
    p.put(ProducerConfig.ACKS_CONFIG,"all");
    p.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG,"true");
    p.put(ProducerConfig.RETRIES_CONFIG,Integer.toString(Integer.MAX_VALUE));
    p.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG,"180000");
    p.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG,"15000");
    List<String> expected=new ArrayList<>();
    long first=-1;
    double retries=0;
    try(KafkaProducer<String,String> producer=new KafkaProducer<>(p)){
      for(int i=0;i<100;i++){
        String value=RUN+"-"+i;
        RecordMetadata m=producer.send(new ProducerRecord<>(TOPIC,0,RUN,value)).get(160,TimeUnit.SECONDS);
        if(i==0)first=m.offset();
        check(m.partition()==0,"Unexpected partition");
        expected.add(value);
        if(i==10)System.out.println("PRODUCER_PROGRESS_10");
        Thread.sleep(80);
      }
      producer.flush();
      for(Map.Entry<MetricName,? extends Metric> entry:producer.metrics().entrySet()){
        if("retry-total".equals(entry.getKey().name()) && "producer-metrics".equals(entry.getKey().group())){
          Object v=entry.getValue().metricValue();
          if(v instanceof Number)retries=((Number)v).doubleValue();
        }
      }
    }
    System.out.println("CHECK:acknowledged_100_records:PASS");
    Properties cp=new Properties();
    cp.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG,BOOT);
    cp.put(ConsumerConfig.GROUP_ID_CONFIG,"ch003-leader-"+RUN);
    cp.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,StringDeserializer.class.getName());
    cp.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,StringDeserializer.class.getName());
    cp.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG,"false");
    TopicPartition tp=new TopicPartition(TOPIC,0);
    List<String> actual=new ArrayList<>();
    try(KafkaConsumer<String,String> c=new KafkaConsumer<>(cp)){
      c.assign(Collections.singletonList(tp));
      c.seek(tp,first);
      long deadline=System.nanoTime()+Duration.ofSeconds(90).toNanos();
      while(actual.size()<100 && System.nanoTime()<deadline)
        for(ConsumerRecord<String,String> record:c.poll(Duration.ofMillis(500)))actual.add(record.value());
      check(c.endOffsets(Collections.singleton(tp)).get(tp)-first==100,"Unexpected records in test offset window");
    }
    check(actual.equals(expected),"Missing, duplicated or reordered records");
    System.out.println("CHECK:ordered_exactly_100_observed:PASS");
    System.out.println("PRODUCER_RETRY_TOTAL:"+retries);
    System.out.println("LEADER_FAILOVER_CLIENT_OK");
  }
}
