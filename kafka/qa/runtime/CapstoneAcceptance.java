import java.nio.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.errors.WakeupException;

/** Short functional application phases: real acknowledgements, forced sink, commits and lag. */
public class CapstoneAcceptance {
  static final int TOTAL=1200;
  static final String[] PHASES={"warmup","baseline","burst","recovery"};
  static final int[] COUNTS={120,360,360,360},RATES={100,200,400,100};
  static int phase(int sequence) {return sequence<120 ? 0 : sequence<480 ? 1 : sequence<840 ? 2 : 3;}
  static final Queue<Throwable> failures=new ConcurrentLinkedQueue<>();
  static void healthy() {PerfAcceptance.check(failures.isEmpty(),"Application observer/consumer failure: "+(failures.isEmpty() ? "none" : failures.peek().getClass().getName()));}
  static Map<String,Object> lag(Admin admin,String phase,long started,int accepted,int processed) throws Exception {
    Map<TopicPartition,Long> ends=ConsumerAcceptance.ends(admin);
    Map<TopicPartition,OffsetAndMetadata> commits=admin.listConsumerGroupOffsets(PerfAcceptance.group).partitionsToOffsetAndMetadata().get(15,TimeUnit.SECONDS);
    Map<String,Long> committed=new TreeMap<>();long backlog=0;
    for(var entry:ends.entrySet()) {long offset=commits.get(entry.getKey())==null ? 0 : commits.get(entry.getKey()).offset();PerfAcceptance.check(offset<=entry.getValue(),"Committed offset exceeds captured end");committed.put(Integer.toString(entry.getKey().partition()),offset);backlog+=entry.getValue()-offset;}
    Map<String,Object> result=new LinkedHashMap<>();result.put("phase",phase);result.put("elapsed_seconds",(System.nanoTime()-started)/1e9);result.put("lag",backlog);result.put("accepted_count",accepted);result.put("forced_sink_count",processed);result.put("captured_ends",ConsumerAcceptance.offsets(ends));result.put("committed_offsets",committed);
    ConsumerAcceptance.emit("APPLICATION_LAG",result);return result;
  }
  static void await(Admin admin,Map<TopicPartition,Long> target,Set<Integer> seen,int count) throws Exception {
    long deadline=System.nanoTime()+Duration.ofSeconds(120).toNanos();
    while(System.nanoTime()<deadline) {healthy();if(seen.size()==count && ConsumerAcceptance.caughtUp(admin,target))return;PerfAcceptance.health(admin);Thread.sleep(100);}
    throw new IllegalStateException("Synthetic application catch-up exceeded bounded budget");
  }
  public static void main(String[] args) throws Exception {
    PerfAcceptance.check(args.length==7 && args[0].equals("phases"),"Expected isolated application phase arguments");
    PerfAcceptance.check(org.apache.kafka.common.utils.AppInfoParser.getVersion().equals("4.0.0"),"Unexpected application client version");
    String id=args[5],trial=args[6];PerfAcceptance.check(trial.matches("r[123]"),"Unapproved application repetition");
    PerfAcceptance.bootstrap=args[1];PerfAcceptance.user=args[2];PerfAcceptance.topic=args[3];PerfAcceptance.group=args[4];PerfAcceptance.trial=trial;PerfAcceptance.partitions=6;
    String targets=String.join(",",java.util.stream.IntStream.range(0,3).mapToObj(i->"qa-kafka-ha-dual-role-"+i+".qa-kafka-ha-kafka-brokers.kafka-qa.svc:9404").toList());
    Path directory=Path.of("/sink"),ledger=directory.resolve("application-"+trial+".log");
    PerfAcceptance.check(Files.isDirectory(directory,LinkOption.NOFOLLOW_LINKS) && !Files.exists(ledger,LinkOption.NOFOLLOW_LINKS),"Owned application sink must be mounted and fresh");
    Set<Integer> accepted=ConcurrentHashMap.newKeySet(),seen=ConcurrentHashMap.newKeySet();AtomicInteger duplicates=new AtomicInteger();
    Queue<Map<String,Object>> eventLedger=new ConcurrentLinkedQueue<>();List<Double> ackLedger=new ArrayList<>();
    List<Queue<Double>> handling=new ArrayList<>(),age=new ArrayList<>();for(int i=0;i<4;i++) {handling.add(new ConcurrentLinkedQueue<>());age.add(new ConcurrentLinkedQueue<>());}
    List<List<Double>> acknowledgements=new ArrayList<>();for(int i=0;i<4;i++)acknowledgements.add(new ArrayList<>());
    AtomicBoolean stop=new AtomicBoolean(),pause=new AtomicBoolean(),paused=new AtomicBoolean();AtomicReference<String> currentPhase=new AtomicReference<>("warmup");AtomicReference<KafkaConsumer<String,String>> consumer=new AtomicReference<>();
    CountDownLatch assigned=new CountDownLatch(1);ScheduledExecutorService observer=Executors.newSingleThreadScheduledExecutor();BrokerAcceptance.Scraper scraper=new BrokerAcceptance.Scraper(targets);
    long started=System.nanoTime();Thread worker=null;boolean sampling=false;
    try(Admin admin=Admin.create(PerfAcceptance.security());FileChannel sink=FileChannel.open(ledger,Set.of(StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE),PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")))) {
      PerfAcceptance.check(sink.tryLock()!=null,"Application sink already has a writer");PerfAcceptance.health(admin);BrokerAcceptance.effective(8);
      PerfAcceptance.check(ConsumerAcceptance.ends(admin).values().stream().mapToLong(Long::longValue).sum()==0,"Application phase topic must be fresh");
      worker=new Thread(()->{
        KafkaConsumer<String,String> c=null;
        try {
          c=new KafkaConsumer<>(ConsumerAcceptance.consumer(id+"-worker"));consumer.set(c);final KafkaConsumer<String,String> owned=c;
          c.subscribe(List.of(PerfAcceptance.topic),new ConsumerRebalanceListener() {
            public void onPartitionsRevoked(Collection<TopicPartition> p) {}
            public void onPartitionsAssigned(Collection<TopicPartition> p) {PerfAcceptance.check(p.size()==6,"Single application worker must own six partitions");assigned.countDown();}
          });
          while(!stop.get()) {
            if(pause.get()) {c.pause(c.assignment());paused.set(true);}else {c.resume(c.assignment());paused.set(false);}
            ConsumerRecords<String,String> batch=c.poll(Duration.ofMillis(200));Map<TopicPartition,OffsetAndMetadata> completed=new HashMap<>();
            if(pause.get() && paused.get())PerfAcceptance.check(batch.isEmpty(),"Paused consumer unexpectedly delivered records");
            for(ConsumerRecord<String,String> record:batch) {
              int sequence=ConsumerAcceptance.eventId(record,id,TOTAL),phase=phase(sequence);long began=System.nanoTime();
              if(!seen.contains(sequence)) {
                Thread.sleep(1);long timestamp=System.currentTimeMillis();
                PerfAcceptance.check(record.timestampType()==org.apache.kafka.common.record.TimestampType.CREATE_TIME && timestamp>=record.timestamp(),"Application event timestamp source invalid");
                ByteBuffer bytes=java.nio.charset.StandardCharsets.UTF_8.encode(id+"|"+sequence+"|"+timestamp+"\n");while(bytes.hasRemaining())sink.write(bytes);sink.force(true);
                double handlerMs=(System.nanoTime()-began)/1e6;long forcedAt=System.currentTimeMillis();handling.get(phase).add(handlerMs);age.get(phase).add((double)(forcedAt-record.timestamp()));
                eventLedger.add(Map.of("sequence",sequence,"created_ms",record.timestamp(),"forced_completion_ms",forcedAt,"handler_and_force_ms",handlerMs));seen.add(sequence);
              }else duplicates.incrementAndGet();
              completed.put(new TopicPartition(record.topic(),record.partition()),new OffsetAndMetadata(record.offset()+1));
            }
            if(!completed.isEmpty())c.commitSync(completed,Duration.ofSeconds(15));
          }
        }catch(WakeupException e) {if(!stop.get())failures.add(e);}catch(Throwable e) {failures.add(e);}finally {consumer.set(null);if(c!=null)try {c.close(Duration.ofSeconds(5));}catch(Throwable e) {failures.add(e);}}
      },"owned-application-worker");worker.start();
      PerfAcceptance.check(assigned.await(60,TimeUnit.SECONDS),"Application consumer did not join");healthy();ConsumerAcceptance.awaitView(admin,1);
      scraper.capture("before");sampling=true;scraper.scheduler.scheduleWithFixedDelay(()->{try {scraper.capture("application_window");}catch(Throwable e) {scraper.failures.add(e);}},0,2,TimeUnit.SECONDS);
      observer.scheduleWithFixedDelay(()->{try {PerfAcceptance.health(admin);lag(admin,currentPhase.get(),started,accepted.size(),seen.size());}catch(Throwable e) {failures.add(e);}},0,500,TimeUnit.MILLISECONDS);
      PerfAcceptance.resourceSnapshot("before");List<Map<String,Object>> phases=new ArrayList<>();int sequence=0;long recoveryStarted=0;Map<String,Object> pausedCheckpoint=null;
      KafkaProducer<String,String> producer=new KafkaProducer<>(ConsumerAcceptance.producer());
      try {
        for(int phase=0;phase<4;phase++) {
          currentPhase.set(PHASES[phase]);
          if(phase==2) {pause.set(true);long deadline=System.nanoTime()+Duration.ofSeconds(10).toNanos();while(!paused.get() && System.nanoTime()<deadline) {healthy();Thread.sleep(10);}PerfAcceptance.check(paused.get(),"Consumer pause barrier not established");}
          if(phase==3) {recoveryStarted=System.nanoTime();lag(admin,"recovery_start",started,accepted.size(),seen.size());pause.set(false);}
          long began=System.nanoTime(),next=began;int phaseFirst=sequence;
          for(int count=0;count<COUNTS[phase];count++,sequence++) {
            healthy();long delay=next-System.nanoTime();if(delay>0)TimeUnit.NANOSECONDS.sleep(delay);next=Math.max(next+1_000_000_000L/RATES[phase],System.nanoTime());
            long created=System.currentTimeMillis(),sent=System.nanoTime();Future<RecordMetadata> result=producer.send(new ProducerRecord<>(PerfAcceptance.topic,sequence%6,created,"synthetic-key",ConsumerAcceptance.event(id,sequence)));
            RecordMetadata metadata;
            while(true) {try {metadata=result.get(200,TimeUnit.MILLISECONDS);break;}catch(java.util.concurrent.TimeoutException e) {healthy();}}
            PerfAcceptance.check(metadata.partition()==sequence%6 && metadata.offset()==sequence/6,"Application acknowledgment partition/offset mismatch");
            accepted.add(sequence);double ackMs=(System.nanoTime()-sent)/1e6;acknowledgements.get(phase).add(ackMs);ackLedger.add(ackMs);
          }
          double producerSeconds=(System.nanoTime()-began)/1e9;Map<TopicPartition,Long> target=ConsumerAcceptance.ends(admin);
          if(phase==2) {pausedCheckpoint=lag(admin,"paused_burst_end",started,accepted.size(),seen.size());PerfAcceptance.check(((Number)pausedCheckpoint.get("lag")).longValue()==COUNTS[phase] && seen.size()==phaseFirst,"Controlled burst did not create the expected uncommitted backlog");}
          else await(admin,target,seen,sequence);
          Map<String,Object> result=new LinkedHashMap<>();result.put("phase",PHASES[phase]);result.put("records",COUNTS[phase]);result.put("offered_cap_records_per_second",RATES[phase]);result.put("acknowledged_records",acknowledgements.get(phase).size());result.put("elapsed_seconds",(System.nanoTime()-began)/1e9);result.put("ack_ms",ConsumerAcceptance.distribution(acknowledgements.get(phase)));result.put("captured_ends",ConsumerAcceptance.offsets(target));result.put("producer_completion_seconds",producerSeconds);result.put("achieved_acknowledgements_per_second",COUNTS[phase]/producerSeconds);result.put("force_sample_count",COUNTS[phase]);result.put("consumer_paused",phase==2);phases.add(result);
        }
      }finally {producer.close(Duration.ofSeconds(5));}
      healthy();PerfAcceptance.check(accepted.size()==TOTAL && seen.equals(accepted),"Accepted/forced-sink event reconciliation failed");
      Map<String,Object> finalLag=lag(admin,"final",started,accepted.size(),seen.size());PerfAcceptance.check(((Number)finalLag.get("lag")).longValue()==0,"Final committed backlog not drained");
      double recoverySeconds=(System.nanoTime()-recoveryStarted)/1e9;
      for(int i=0;i<4;i++) {phases.get(i).put("force_sample_count",handling.get(i).size());phases.get(i).put("handler_and_force_ms",ConsumerAcceptance.distribution(handling.get(i)));phases.get(i).put("created_to_forced_sink_ms",ConsumerAcceptance.distribution(age.get(i)));}
      observer.shutdown();PerfAcceptance.check(observer.awaitTermination(20,TimeUnit.SECONDS),"Application observer did not stop");scraper.finish();sampling=false;healthy();
      stop.set(true);KafkaConsumer<String,String> c=consumer.get();if(c!=null)c.wakeup();worker.join(10000);PerfAcceptance.check(!worker.isAlive(),"Application worker did not stop");healthy();
      List<String> durable=Files.readAllLines(ledger);Set<Integer> durableIds=new HashSet<>();for(String line:durable) {String[] fields=line.split("\\|");PerfAcceptance.check(fields.length==3 && fields[0].equals(id) && Long.parseLong(fields[2])>0 && durableIds.add(Integer.parseInt(fields[1])),"Durable sink ledger identity/timestamp/duplicate mismatch");}
      PerfAcceptance.check(durableIds.equals(accepted),"Reloaded forced ledger differs from accepted IDs");
      PerfAcceptance.resourceSnapshot("after");ConsumerAcceptance.emit("APPLICATION_EVENT_LEDGER",eventLedger);ConsumerAcceptance.emit("APPLICATION_ACK_LEDGER_MS",ackLedger);ConsumerAcceptance.emit("APPLICATION_PHASES",Map.of("event_id_prefix",id,"phases",phases,"accepted_sequence_ids",new TreeSet<>(accepted),"forced_sink_sequence_ids",new TreeSet<>(durableIds),"duplicate_attempts",duplicates.get(),"missing_accepted_ids",0,"recovery_seconds",recoverySeconds,"paused_burst_backlog",COUNTS[2],"ledger_sha256",PerfAcceptance.digest(Files.readAllBytes(ledger)),"scope","short functional phases; timestamped forced synthetic file, not external DB or production capacity"));
      PerfAcceptance.pass("actual_application_phases_ack_force_commit_and_no_missing_ids");PerfAcceptance.pass("paused_burst_backlog_drains_with_new_ingress_and_final_commits");PerfAcceptance.health(admin);PerfAcceptance.pass("secure_full_isr_quorum_and_bounded_application_shutdown");
    }finally {
      stop.set(true);KafkaConsumer<String,String> c=consumer.get();if(c!=null)c.wakeup();observer.shutdownNow();if(sampling)scraper.finish();else scraper.scheduler.shutdownNow();if(worker!=null && worker.isAlive())worker.join(10000);
    }
  }
}
