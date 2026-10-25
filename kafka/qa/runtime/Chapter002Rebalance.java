import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;

public class Chapter002Rebalance {
  static final String TOPIC = "qa-ch002-ordering";
  static final String BOOT = "qa-six-kafka-bootstrap:9092";
  static final String GROUP = "ch002-rebalance-__RUN__";
  static final AtomicReference<Throwable> failure = new AtomicReference<>();
  static class Worker implements Runnable {
    final String id;
    final AtomicBoolean active = new AtomicBoolean(true);
    final AtomicReference<Set<Integer>> assignment = new AtomicReference<>(Collections.emptySet());
    final AtomicInteger revocations = new AtomicInteger();
    final AtomicInteger assignments = new AtomicInteger();
    final AtomicInteger messages = new AtomicInteger();
    Worker(String id) { this.id = id; }
    public void run() {
      Properties p = new Properties();
      p.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, BOOT);
      p.put(ConsumerConfig.GROUP_ID_CONFIG, GROUP);
      p.put(ConsumerConfig.CLIENT_ID_CONFIG, "ch002-"+id);
      p.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
      p.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
      p.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
      p.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
      p.put(ConsumerConfig.PARTITION_ASSIGNMENT_STRATEGY_CONFIG, "org.apache.kafka.clients.consumer.CooperativeStickyAssignor");
      try (KafkaConsumer<String,String> c = new KafkaConsumer<>(p)) {
        c.subscribe(Collections.singletonList(TOPIC), new ConsumerRebalanceListener() {
          public void onPartitionsRevoked(Collection<TopicPartition> parts) {
            revocations.incrementAndGet();
            assignment.set(Collections.emptySet());
          }
          public void onPartitionsAssigned(Collection<TopicPartition> parts) {
            Set<Integer> set = new TreeSet<>();
            for (TopicPartition tp : parts) set.add(tp.partition());
            assignment.set(Collections.unmodifiableSet(set));
            assignments.incrementAndGet();
          }
        });
        while (active.get()) {
          ConsumerRecords<String,String> records = c.poll(Duration.ofMillis(250));
          messages.addAndGet(records.count());
          if (!records.isEmpty()) c.commitSync(Duration.ofSeconds(10));
        }
      } catch (Throwable t) { failure.compareAndSet(null,t); }
    }
  }
  static void check() {
    if (failure.get()!=null) throw new RuntimeException("Consumer failed",failure.get());
  }
  static void await(String label, java.util.function.BooleanSupplier condition) throws Exception {
    long until=System.nanoTime()+Duration.ofSeconds(80).toNanos();
    while(System.nanoTime()<until) {
      check();
      if(condition.getAsBoolean()) return;
      Thread.sleep(300);
    }
    throw new IllegalStateException("Timed out waiting for "+label);
  }
  static boolean distributed(Worker a, Worker b) {
    Set<Integer> x=a.assignment.get(), y=b.assignment.get();
    Set<Integer> union=new HashSet<>(x);
    union.addAll(y);
    Set<Integer> intersection=new HashSet<>(x);
    intersection.retainAll(y);
    return !x.isEmpty() && !y.isEmpty() && union.size()==3 && intersection.isEmpty();
  }
  public static void main(String[] args) throws Exception {
    Worker a=new Worker("A"), b=new Worker("B");
    Thread ta=new Thread(a,"consumer-A"), tb=new Thread(b,"consumer-B");
    try {
      ta.start();
      await("single consumer owning 3 partitions", ()->a.assignment.get().size()==3);
      System.out.println("CHECK:single_consumer_three_partitions:PASS");
      tb.start();
      await("two consumers sharing three partitions", ()->distributed(a,b));
      System.out.println("CHECK:balanced_group_assignment:PASS");
      System.out.println("ASSIGNMENTS:before:A="+a.assignment.get()+":B="+b.assignment.get());
      b.active.set(false);
      tb.join(20000);
      if(tb.isAlive()) throw new IllegalStateException("Consumer B did not stop");
      await("surviving consumer owns all partitions", ()->a.assignment.get().size()==3);
      System.out.println("CHECK:survivor_reassigned_three_partitions:PASS");
      Worker c=new Worker("C");
      Thread tc=new Thread(c,"consumer-C");
      try {
        tc.start();
        await("replacement consumer triggers rebalance", ()->distributed(a,c));
        System.out.println("CHECK:replacement_consumer_rebalance:PASS");
        System.out.println("ASSIGNMENTS:after:A="+a.assignment.get()+":C="+c.assignment.get());
        System.out.println("REBALANCE_OK");
      } finally {
        c.active.set(false);
        tc.join(20000);
        if(tc.isAlive()) throw new IllegalStateException("Consumer C did not stop");
      }
    } finally {
      a.active.set(false); b.active.set(false);
      ta.join(20000); tb.join(20000);
    }
    check();
  }
}
