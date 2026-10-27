import java.io.*;
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
import org.apache.kafka.common.errors.*;
import org.apache.kafka.common.record.TimestampType;
import org.apache.kafka.common.utils.AppInfoParser;

/** Functional consumer studies; helper code is bundled after this public main class. */
public class ConsumerAcceptance {
  static final int EVENTS=120;
  static void check(boolean value,String message) {PerfAcceptance.check(value,message);}
  static void pass(String name) {PerfAcceptance.pass(name);}
  static String quote(String value) {return "\""+value.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";}
  static String json(Object value) {
    if(value==null)return "null";if(value instanceof String)return quote((String)value);if(value instanceof Number || value instanceof Boolean)return value.toString();
    if(value instanceof Map<?,?> map) {List<String> fields=new ArrayList<>();map.forEach((k,v)->fields.add(quote(k.toString())+":"+json(v)));return "{"+String.join(",",fields)+"}";}
    if(value instanceof Collection<?> list)return "["+String.join(",",list.stream().map(ConsumerAcceptance::json).toList())+"]";
    throw new IllegalStateException("Unsupported safe JSON evidence type");
  }
  static void emit(String name,Object value) {System.out.println("OBS:"+name+":"+json(value));}
  static void context(String bootstrap,String user,String topic,String group,String trial) {
    check(AppInfoParser.getVersion().equals("4.0.0"),"Unexpected consumer client version");
    PerfAcceptance.bootstrap=bootstrap;PerfAcceptance.user=user;PerfAcceptance.topic=topic;PerfAcceptance.group=group;PerfAcceptance.trial=trial;
    PerfAcceptance.partitions=6;PerfAcceptance.records=1200;PerfAcceptance.size=1024;PerfAcceptance.rate=400;PerfAcceptance.payloadMode="native-random";
  }
  static Properties consumer(String client) throws Exception {
    Properties p=PerfAcceptance.security();p.put("group.id",PerfAcceptance.group);p.put("client.id",client);p.put("group.protocol","classic");
    p.put("partition.assignment.strategy","org.apache.kafka.clients.consumer.RangeAssignor");p.put("enable.auto.commit","false");p.put("auto.offset.reset","earliest");
    p.put("session.timeout.ms","10000");p.put("heartbeat.interval.ms","3000");p.put("max.poll.interval.ms","120000");p.put("max.poll.records","100");
    p.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");p.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");return p;
  }
  static Properties producer() throws Exception {
    Properties p=PerfAcceptance.security();p.put("acks","all");p.put("enable.idempotence","true");p.put("linger.ms","0");p.put("batch.size","16384");p.put("compression.type","none");
    p.put("max.in.flight.requests.per.connection","5");p.put("max.block.ms","15000");p.put("delivery.timeout.ms","30000");
    p.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");p.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");return p;
  }
  static Map<TopicPartition,Long> ends(Admin admin) throws Exception {
    Map<TopicPartition,OffsetSpec> query=new HashMap<>();for(int i=0;i<6;i++)query.put(new TopicPartition(PerfAcceptance.topic,i),OffsetSpec.latest());
    Map<TopicPartition,Long> result=new HashMap<>();admin.listOffsets(query).all().get(15,TimeUnit.SECONDS).forEach((p,o)->result.put(p,o.offset()));return result;
  }
  static Map<String,Long> offsets(Map<TopicPartition,Long> values) {Map<String,Long> result=new TreeMap<>();values.forEach((p,o)->result.put(Integer.toString(p.partition()),o));return result;}
  static boolean caughtUp(Admin admin,Map<TopicPartition,Long> targets) throws Exception {
    Map<TopicPartition,OffsetAndMetadata> committed=admin.listConsumerGroupOffsets(PerfAcceptance.group).partitionsToOffsetAndMetadata().get(15,TimeUnit.SECONDS);
    for(var entry:targets.entrySet())if(committed.get(entry.getKey())==null || committed.get(entry.getKey()).offset()!=entry.getValue())return false;
    return true;
  }
  static String event(String id,int sequence) {String header=id+"|"+sequence+"|";check(header.length()<1024,"Event ID too long");return header+"A".repeat(1024-header.length());}
  static int eventId(ConsumerRecord<String,String> record,String id,int count) {
    String[] pieces=record.value().split("\\|",3);check(pieces.length==3 && pieces[0].equals(id) && record.key().equals("synthetic-key"),"Synthetic event key/identity mismatch");
    int sequence=Integer.parseInt(pieces[1]);check(sequence>=0 && sequence<count && record.partition()==sequence%6 && record.value().equals(event(id,sequence)),"Synthetic event partition/value mismatch");return sequence;
  }
  static Map<TopicPartition,Long> seed(Admin admin,String id,int count) throws Exception {
    check(count>0 && count<=EVENTS && count%6==0,"Unapproved synthetic seed budget");PerfAcceptance.health(admin);Map<TopicPartition,Long> before=ends(admin);
    try(KafkaProducer<String,String> p=new KafkaProducer<>(producer())) {
      for(int i=0;i<count;i++) {
        if(i%12==0)PerfAcceptance.health(admin);
        RecordMetadata ack=p.send(new ProducerRecord<>(PerfAcceptance.topic,i%6,"synthetic-key",event(id,i))).get(35,TimeUnit.SECONDS);
        check(ack.offset()==before.get(new TopicPartition(PerfAcceptance.topic,i%6))+i/6,"Seed acknowledgment offset mismatch");
      }
    }
    Map<TopicPartition,Long> after=ends(admin);for(int i=0;i<6;i++)check(after.get(new TopicPartition(PerfAcceptance.topic,i))==before.get(new TopicPartition(PerfAcceptance.topic,i))+count/6,"Seed log ends mismatch");
    emit("CONSUMER_SEED",Map.of("event_id",id,"records",count,"before",offsets(before),"after",offsets(after),"acks","all"));return after;
  }
  static void fetch(String[] args) throws Exception {
    check(args.length==12,"Expected approved native fetch profile");context(args[0],args[1],args[2],args[3],args[4]);
    PerfAcceptance.records=Integer.parseInt(args[5]);PerfAcceptance.size=Integer.parseInt(args[6]);PerfAcceptance.rate=Integer.parseInt(args[7]);
    int minimum=Integer.parseInt(args[8]),wait=Integer.parseInt(args[9]),partitionFetch=Integer.parseInt(args[10]),poll=Integer.parseInt(args[11]);
    check(Set.of(120,1200).contains(PerfAcceptance.records) && PerfAcceptance.size==1024 && PerfAcceptance.rate==400 && Set.of(1,16384,65536).contains(minimum)
      && Set.of(100,500,1000).contains(wait) && Set.of(65536,1048576).contains(partitionFetch) && Set.of(100,500).contains(poll),"Unapproved native fetch payload/configuration");
    Path directory=Files.createTempDirectory("restricted-consumer-",PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
    Path pp=directory.resolve("producer.properties"),cp=directory.resolve("consumer.properties"),logging=directory.resolve("logging.xml");
    try(Admin admin=Admin.create(PerfAcceptance.security())) {
      Properties p=producer();p.remove("key.serializer");p.remove("value.serializer");PerfAcceptance.writeConfig(pp,p);
      Properties c=consumer("native-fetch");c.put("fetch.min.bytes",Integer.toString(minimum));c.put("fetch.max.wait.ms",Integer.toString(wait));c.put("fetch.max.bytes","1048576");c.put("max.partition.fetch.bytes",Integer.toString(partitionFetch));c.put("max.poll.records",Integer.toString(poll));
      c.remove("key.deserializer");c.remove("value.deserializer");PerfAcceptance.writeConfig(cp,c);
      Files.writeString(logging,"<Configuration status=\"ERROR\"><Appenders><Console name=\"Console\" target=\"SYSTEM_ERR\"><PatternLayout pattern=\"%level %message%n\"/></Console></Appenders><Loggers><Root level=\"warn\"><AppenderRef ref=\"Console\"/></Root></Loggers></Configuration>");
      PerfAcceptance.health(admin);PerfAcceptance.resourceSnapshot("before");
      emit("CONSUMER_PROFILE",Map.of("group.protocol","classic","fetch.min.bytes",minimum,"fetch.max.wait.ms",wait,"max.partition.fetch.bytes",partitionFetch,"max.poll.records",poll,"enable.auto.commit",false,"scope","native fetch, not business processing"));
      if(PerfAcceptance.trial.equals("warmup"))PerfAcceptance.execute(admin,logging,30,"/opt/kafka/bin/kafka-consumer-perf-test.sh","--help");
      long started=System.nanoTime();PerfAcceptance.execute(admin,logging,90,PerfAcceptance.producerCommand(pp,directory.resolve("unused-payload")));pass("native_producer_process_completed_acks_all_idempotent");
      PerfAcceptance.execute(admin,logging,60,"/opt/kafka/bin/kafka-consumer-perf-test.sh","--bootstrap-server",PerfAcceptance.bootstrap,"--topic",PerfAcceptance.topic,"--messages",Integer.toString(PerfAcceptance.records),"--group",PerfAcceptance.group,
        "--timeout","30000","--consumer.config",cp.toString(),"--fetch-size",Integer.toString(partitionFetch),"--print-metrics");pass("native_consumer_process_completed");
      PerfAcceptance.audit(admin);PerfAcceptance.health(admin);PerfAcceptance.resourceSnapshot("after");emit("FETCH_TRIAL",Map.of("completion_seconds",(System.nanoTime()-started)/1e9,"health_samples",PerfAcceptance.healthSamples,"consumer_latency_percentiles","NOT_REPORTED_BY_NATIVE_CSV"));pass("full_isr_quorum_polling_and_final_health");
    } finally {Files.deleteIfExists(pp);Files.deleteIfExists(cp);Files.deleteIfExists(logging);Files.deleteIfExists(directory);}
  }

  static Map<String,Object> view(Admin admin,int expected) throws Exception {
    ConsumerGroupDescription description=admin.describeConsumerGroups(List.of(PerfAcceptance.group)).describedGroups().get(PerfAcceptance.group).get(15,TimeUnit.SECONDS);
    if(description.groupState()!=GroupState.STABLE || description.members().size()!=expected)return null;
    check(description.type()==GroupType.CLASSIC && description.partitionAssignor().equals("range"),"Unexpected group protocol/assignor");
    Set<Integer> coverage=new TreeSet<>();List<Map<String,Object>> members=new ArrayList<>();int active=0;
    for(MemberDescription member:description.members()) {
      List<Integer> assigned=new ArrayList<>();
      for(TopicPartition partition:member.assignment().topicPartitions()) {
        check(partition.topic().equals(PerfAcceptance.topic) && partition.partition()>=0 && partition.partition()<6 && coverage.add(partition.partition()),"Missing/duplicate/foreign group assignment");assigned.add(partition.partition());
      }
      Collections.sort(assigned);if(!assigned.isEmpty())active++;
      members.add(Map.of("client_id",member.clientId(),"member_id",member.consumerId(),"host",member.host(),"partitions",assigned));
    }
    check(coverage.size()==6 && active==Math.min(6,expected),"Exclusive assignment ceiling/coverage failed");members.sort(Comparator.comparing(member->member.get("client_id").toString()));
    Map<String,Object> result=new LinkedHashMap<>();result.put("group",PerfAcceptance.group);result.put("state",description.groupState().toString());result.put("protocol","classic");result.put("assignor",description.partitionAssignor());
    result.put("member_count",expected);result.put("active",active);result.put("idle",expected-active);result.put("members",members);return result;
  }
  static Map<String,Object> awaitView(Admin admin,int expected) throws Exception {
    long deadline=System.nanoTime()+Duration.ofSeconds(120).toNanos();String last="not stable";
    while(System.nanoTime()<deadline) {
      try {Map<String,Object> result=view(admin,expected);if(result!=null)return result;}
      catch(ExecutionException e) {if(e.getCause() instanceof AuthorizationException || e.getCause() instanceof AuthenticationException)throw e;last=e.getCause().getClass().getSimpleName();}
      PerfAcceptance.health(admin);Thread.sleep(200);
    }throw new IllegalStateException("Group did not converge to expected stable membership: "+last);
  }
  static void awaitCaughtUp(Admin admin,Map<TopicPartition,Long> target) throws Exception {
    long deadline=System.nanoTime()+Duration.ofSeconds(120).toNanos();
    while(System.nanoTime()<deadline) {if(caughtUp(admin,target))return;PerfAcceptance.health(admin);Thread.sleep(200);}
    throw new IllegalStateException("Committed offsets did not reach captured ends within bounded catch-up budget");
  }
  static Map<String,Double> distribution(Collection<Double> samples) {
    check(!samples.isEmpty(),"Missing real latency observations");List<Double> sorted=new ArrayList<>(samples);Collections.sort(sorted);
    return Map.of("p50",sorted.get((int)Math.ceil(sorted.size()*.50)-1),"p95",sorted.get((int)Math.ceil(sorted.size()*.95)-1),"p99",sorted.get((int)Math.ceil(sorted.size()*.99)-1),"maximum",sorted.get(sorted.size()-1));
  }
  static class Participant implements Runnable {
    final int number;final String id;final AtomicBoolean gate,stop;final ConcurrentHashMap<Integer,Boolean> seen;final Queue<Double> handling,age;final Queue<Throwable> errors;
    final AtomicInteger duplicates;final AtomicBoolean paused=new AtomicBoolean();volatile KafkaConsumer<String,String> client;volatile int revoked,assigned,processed;
    Participant(int number,String id,AtomicBoolean gate,AtomicBoolean stop,ConcurrentHashMap<Integer,Boolean> seen,Queue<Double> handling,Queue<Double> age,Queue<Throwable> errors,AtomicInteger duplicates) {
      this.number=number;this.id=id;this.gate=gate;this.stop=stop;this.seen=seen;this.handling=handling;this.age=age;this.errors=errors;this.duplicates=duplicates;
    }
    public void run() {
      try(KafkaConsumer<String,String> c=new KafkaConsumer<>(consumer(id+"-member-"+number))) {
        client=c;c.subscribe(List.of(PerfAcceptance.topic),new ConsumerRebalanceListener() {
          public void onPartitionsRevoked(Collection<TopicPartition> p) {revoked++;paused.set(false);}
          public void onPartitionsAssigned(Collection<TopicPartition> p) {assigned++;if(!gate.get())c.pause(p);paused.set(true);}
        });
        while(!stop.get()) {
          if(gate.get())c.resume(c.assignment());else c.pause(c.assignment());
          ConsumerRecords<String,String> records=c.poll(Duration.ofMillis(200));
          if(!gate.get()) {check(records.isEmpty(),"Data arrived before controlled processing release");if(!c.groupMetadata().memberId().isEmpty())paused.set(true);continue;}
          Map<TopicPartition,OffsetAndMetadata> completed=new HashMap<>();
          for(ConsumerRecord<String,String> record:records) {
            int event=eventId(record,id,EVENTS);
            seen.compute(event,(key,previous)->{
              if(previous!=null) {duplicates.incrementAndGet();return previous;}
              long started=System.nanoTime();try {Thread.sleep(1);}catch(InterruptedException e) {throw new IllegalStateException(e);}
              check(record.timestampType()==TimestampType.CREATE_TIME && System.currentTimeMillis()>=record.timestamp(),"Event-age clock/timestamp source invalid");
              handling.add((System.nanoTime()-started)/1e6);age.add((double)(System.currentTimeMillis()-record.timestamp()));return true;
            });
            processed++;completed.put(new TopicPartition(record.topic(),record.partition()),new OffsetAndMetadata(record.offset()+1));
          }
          if(!completed.isEmpty())c.commitSync(completed,Duration.ofSeconds(15));
        }
      }catch(WakeupException e) {if(!stop.get())errors.add(e);}catch(Throwable e) {errors.add(e);System.err.println("Consumer participant failed: "+e.getClass().getName());}finally {client=null;}
    }
    void wake() {KafkaConsumer<String,String> current=client;if(current!=null)current.wakeup();}
  }
  static void parallel(String[] args) throws Exception {
    check(args.length==6,"Expected consumer parallelism arguments");int count=Integer.parseInt(args[4]);String id=args[5];check(Set.of(1,3,6,8).contains(count),"Unapproved member budget");context(args[0],args[1],args[2],args[3],id);
    AtomicBoolean gate=new AtomicBoolean(),stop=new AtomicBoolean();ConcurrentHashMap<Integer,Boolean> seen=new ConcurrentHashMap<>();Queue<Double> handling=new ConcurrentLinkedQueue<>(),age=new ConcurrentLinkedQueue<>();Queue<Throwable> errors=new ConcurrentLinkedQueue<>();AtomicInteger duplicates=new AtomicInteger();
    List<Participant> workers=new ArrayList<>();List<Thread> threads=new ArrayList<>();
    try(Admin admin=Admin.create(PerfAcceptance.security())) {
      PerfAcceptance.health(admin);check(ends(admin).values().stream().mapToLong(Long::longValue).sum()==0,"Parallelism topic must be fresh");
      for(int i=0;i<count;i++) {Participant worker=new Participant(i,id,gate,stop,seen,handling,age,errors,duplicates);workers.add(worker);Thread thread=new Thread(worker,"consumer-"+i);threads.add(thread);thread.start();}
      Map<String,Object> assignment=awaitView(admin,count);long readyDeadline=System.nanoTime()+Duration.ofSeconds(30).toNanos();
      while(workers.stream().anyMatch(worker->!worker.paused.get()) && System.nanoTime()<readyDeadline) {check(errors.isEmpty(),"Consumer worker failed before seed");Thread.sleep(100);}
      check(workers.stream().allMatch(worker->worker.paused.get()) && errors.isEmpty(),"Members did not reach controlled pause barrier");pass("exclusive_six_partition_assignment_and_idle_ceiling");
      Map<TopicPartition,Long> target=seed(admin,id,EVENTS);PerfAcceptance.resourceSnapshot("before");long started=System.nanoTime();gate.set(true);
      long deadline=System.nanoTime()+Duration.ofSeconds(120).toNanos();
      while(seen.size()<EVENTS && System.nanoTime()<deadline) {check(errors.isEmpty(),"Consumer worker failed during processing");PerfAcceptance.health(admin);Thread.sleep(100);}
      check(seen.size()==EVENTS && errors.isEmpty(),"Synthetic application processing incomplete");awaitCaughtUp(admin,target);assignment=awaitView(admin,count);PerfAcceptance.health(admin);
      double elapsed=(System.nanoTime()-started)/1e9;PerfAcceptance.resourceSnapshot("after");
      List<Map<String,Object>> observations=new ArrayList<>();for(Participant worker:workers)observations.add(Map.of("client_id",id+"-member-"+worker.number,"processed_attempts",worker.processed,"assignment_callbacks",worker.assigned,"revocation_callbacks",worker.revoked));
      emit("GROUP_FUNCTIONAL",Map.of("assignment",assignment,"unique_processed",seen.size(),"duplicate_attempts",duplicates.get(),"completion_seconds",elapsed,"handler_ms",distribution(handling),"event_age_ms",distribution(age),"captured_ends",offsets(target),"workers",observations,"execution_scope","member threads in one Pod, not Deployment replica throughput"));
      pass("processed_ids_commit_after_success_and_captured_end_catchup");pass("healthy_quorum_and_full_isr");
    } finally {stop.set(true);workers.forEach(Participant::wake);for(Thread thread:threads) {thread.join(10000);check(!thread.isAlive(),"Consumer worker did not stop within bounded shutdown");}check(errors.isEmpty(),"Consumer participants failed during shutdown");}
  }

  static void workerResources(String pod) {
    Map<String,Object> result=new LinkedHashMap<>();result.put("pod",pod);result.put("timestamp_utc",java.time.Instant.now().toString());result.put("scope","cumulative consumer Pod cgroup snapshot, not broker utilization");
    for(String field:List.of("cpu.stat","memory.current","memory.peak"))try {result.put(field,Files.readString(Path.of("/sys/fs/cgroup/"+field)).trim().replace('\n',';'));}catch(IOException e) {result.put(field,null);}
    emit("WORKER_CGROUP",result);
  }
  static void worker(String[] args) throws Exception {
    check(args.length==5,"Expected approved consumer worker arguments");String pod=System.getenv("POD_NAME");check(pod!=null && pod.matches("[a-z0-9-]+"),"Missing actual downward-API Pod identity");
    context(args[0],args[1],args[2],args[3],"worker");String prefix=args[4];Path ready=Path.of("/tmp/consumer-joined");AtomicBoolean stop=new AtomicBoolean();AtomicReference<KafkaConsumer<String,String>> reference=new AtomicReference<>();CountDownLatch done=new CountDownLatch(1);
    Runtime.getRuntime().addShutdownHook(new Thread(()->{stop.set(true);KafkaConsumer<String,String> c=reference.get();if(c!=null)c.wakeup();try {done.await(20,TimeUnit.SECONDS);}catch(InterruptedException ignored) {}}));
    try(KafkaConsumer<String,String> c=new KafkaConsumer<>(consumer(pod))) {
      reference.set(c);c.subscribe(List.of(PerfAcceptance.topic),new ConsumerRebalanceListener() {
        public void onPartitionsRevoked(Collection<TopicPartition> p) {try {Files.deleteIfExists(ready);}catch(IOException e) {throw new UncheckedIOException(e);}}
        public void onPartitionsAssigned(Collection<TopicPartition> p) {try {Files.writeString(ready,"joined");}catch(IOException e) {throw new UncheckedIOException(e);}}
      });
      long deadline=System.nanoTime()+Duration.ofMinutes(12).toNanos();
      while(!stop.get() && System.nanoTime()<deadline) {
        ConsumerRecords<String,String> records=c.poll(Duration.ofMillis(200));Map<TopicPartition,OffsetAndMetadata> completed=new HashMap<>();
        for(ConsumerRecord<String,String> record:records) {
          String[] fields=record.value().split("\\|",3);check(fields.length==3 && fields[0].startsWith(prefix),"Unexpected synthetic scaling event");int event=eventId(record,fields[0],EVENTS);
          long started=System.nanoTime();Thread.sleep(1);check(record.timestampType()==TimestampType.CREATE_TIME && System.currentTimeMillis()>=record.timestamp(),"Worker timestamp source invalid");
          emit("WORKER_PROCESSED",Map.of("pod",pod,"partition",record.partition(),"offset",record.offset(),"event_id",fields[0]+"-"+event,"handler_ms",(System.nanoTime()-started)/1e6,"event_age_ms",System.currentTimeMillis()-record.timestamp(),"processing_scope","synthetic validation, not external durable side effects"));
          completed.put(new TopicPartition(record.topic(),record.partition()),new OffsetAndMetadata(record.offset()+1));
        }
        if(!completed.isEmpty()) {c.commitSync(completed,Duration.ofSeconds(15));workerResources(pod);}
      }
    }catch(WakeupException e) {if(!stop.get())throw e;}finally {Files.deleteIfExists(ready);done.countDown();}
  }
  static void inspect(String[] args) throws Exception {
    check(args.length==6,"Expected scaling inspector arguments");int count=Integer.parseInt(args[4]);check(Set.of(1,3,6).contains(count),"Unapproved Deployment replica budget");context(args[0],args[1],args[2],args[3],"scale-"+count);
    try(Admin admin=Admin.create(PerfAcceptance.security())) {
      Map<String,Object> assignment=awaitView(admin,count);Map<TopicPartition,Long> before=ends(admin);if(before.values().stream().mapToLong(Long::longValue).sum()>0)awaitCaughtUp(admin,before);
      long started=System.nanoTime();Map<TopicPartition,Long> target=seed(admin,args[5],6);awaitCaughtUp(admin,target);assignment=awaitView(admin,count);PerfAcceptance.health(admin);
      emit("SCALE_GROUP",Map.of("assignment",assignment,"canary_records",6,"before",offsets(before),"after",offsets(target),"committed_lag_against_captured_ends",0,"completion_seconds",(System.nanoTime()-started)/1e9,"scope","manual Deployment scaling, not HPA/KEDA certification"));
      pass("stable_membership_and_committed_canary");pass("healthy_quorum_and_full_isr");
    }
  }
  static void seedMode(String[] args) throws Exception {
    check(args.length==5,"Expected isolated seed arguments");int count=Integer.parseInt(args[4]);context(args[0],args[1],args[2],"unused-seed-group","seed");
    try(Admin admin=Admin.create(PerfAcceptance.security())) {Map<TopicPartition,Long> before=ends(admin);check(before.values().stream().mapToLong(Long::longValue).sum()==0,"Replay seed topic not fresh");seed(admin,args[3],count);PerfAcceptance.health(admin);pass("bounded_six_partition_seed_acks_all");}
  }
  static Set<Integer> loadLedger(Path file) throws Exception {
    check(Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS),"Owned sink ledger absent or not a regular file");Set<Integer> seen=new HashSet<>();
    for(String line:Files.readAllLines(file)) {int id=Integer.parseInt(line);check(id>=0 && id<EVENTS && seen.add(id),"Invalid/duplicate durable sink event ID");}return seen;
  }
  static void appendForced(FileChannel file,int id) throws Exception {
    ByteBuffer bytes=java.nio.charset.StandardCharsets.UTF_8.encode(Integer.toString(id)+"\n");while(bytes.hasRemaining())file.write(bytes);file.force(true);
  }
  static void replay(String[] args,boolean crash) throws Exception {
    check(args.length==5,"Expected owned replay arguments");String id=args[4];context(args[0],args[1],args[2],args[3],crash ? "replay-crash" : "replay-recover");
    Path directory=Path.of("/sink"),ledger=directory.resolve("events.log");check(Files.isDirectory(directory,LinkOption.NOFOLLOW_LINKS),"Owned sink PVC mount missing");
    Set<Integer> seen;
    if(crash) {check(!Files.exists(ledger,LinkOption.NOFOLLOW_LINKS),"Replay crash ledger was not fresh");Files.createFile(ledger,PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")));seen=new HashSet<>();}
    else {seen=loadLedger(ledger);check(seen.size()==12,"Fresh recovery process did not observe the 12 forced pre-commit IDs");emit("SINK_RELOADED",Map.of("persisted_ids",seen.size(),"scope","same owned PVC, process-level persistence"));}
    int replays=0;long started=System.nanoTime();
    try(Admin admin=Admin.create(PerfAcceptance.security());FileChannel file=FileChannel.open(ledger,StandardOpenOption.WRITE,StandardOpenOption.APPEND,LinkOption.NOFOLLOW_LINKS);KafkaConsumer<String,String> c=new KafkaConsumer<>(consumer(crash ? "crash-client" : "recovery-client"))) {
      FileLock lock=file.tryLock();check(lock!=null,"Owned sink ledger already has a writer");PerfAcceptance.health(admin);Map<TopicPartition,Long> target=ends(admin);check(target.values().stream().mapToLong(Long::longValue).sum()==EVENTS,"Unexpected replay backlog");
      c.subscribe(List.of(PerfAcceptance.topic));long deadline=System.nanoTime()+Duration.ofSeconds(120).toNanos();
      while(System.nanoTime()<deadline) {
        ConsumerRecords<String,String> batch=c.poll(Duration.ofMillis(200));Map<TopicPartition,OffsetAndMetadata> completed=new HashMap<>();
        for(ConsumerRecord<String,String> record:batch) {
          int event=eventId(record,id,EVENTS);
          if(seen.add(event))appendForced(file,event);else replays++;
          completed.put(new TopicPartition(record.topic(),record.partition()),new OffsetAndMetadata(record.offset()+1));
          if(crash && seen.size()==12) {
            Map<String,Object> committed=new TreeMap<>();Map<String,Long> positions=new TreeMap<>();Set<TopicPartition> assignment=c.assignment();check(assignment.size()==6,"Crash group did not own six partitions");
            Map<TopicPartition,OffsetAndMetadata> offsets=c.committed(assignment,Duration.ofSeconds(15));long positionSum=0;
            for(TopicPartition partition:assignment) {positions.put(Integer.toString(partition.partition()),c.position(partition));positionSum+=c.position(partition);OffsetAndMetadata value=offsets.get(partition);committed.put(Integer.toString(partition.partition()),value==null ? null : value.offset());check(value==null || value.offset()==0,"Crash checkpoint unexpectedly committed processed data");}
            check(positionSum>seen.size(),"Poll position did not demonstrate processed/committed separation");emit("REPLAY_CHECKPOINT",Map.of("forced_unique_ids",seen.size(),"consumer_positions",positions,"committed_offsets",committed,"expected_process_exit",23,"commit_after_checkpoint",false));
            pass("forced_sink_checkpoint_before_commit_expected_halt");System.out.flush();System.err.flush();Runtime.getRuntime().halt(23);
          }
        }
        if(!crash && !completed.isEmpty())c.commitSync(completed,Duration.ofSeconds(15));
        if(!crash && seen.size()==EVENTS && caughtUp(admin,target)) {
          check(replays>=12 && loadLedger(ledger).size()==EVENTS,"Replay/idempotent sink ledger reconciliation failed");PerfAcceptance.health(admin);file.force(true);
          emit("REPLAY_RECOVERY",Map.of("unique_sink_ids",seen.size(),"duplicate_replay_attempts",replays,"committed_ends",offsets(target),"ledger_sha256",PerfAcceptance.digest(Files.readAllBytes(ledger)),"completion_seconds",(System.nanoTime()-started)/1e9,"processing_scope","single-writer forced synthetic file, not external DB exactly-once or node failure resilience"));
          pass("replayed_uncommitted_ids_deduplicated_and_no_missing_ids");pass("commit_after_success_reaches_captured_ends");return;
        }
        PerfAcceptance.health(admin);
      }throw new IllegalStateException("Replay phase exceeded bounded deadline");
    }
  }
  public static void main(String[] args) throws Exception {
    check(args.length>0,"Consumer acceptance mode missing");String[] values=Arrays.copyOfRange(args,1,args.length);
    switch(args[0]) {
      case "fetch" -> fetch(values);
      case "parallel" -> parallel(values);
      case "worker" -> worker(values);
      case "inspect" -> inspect(values);
      case "seed" -> seedMode(values);
      case "replay-crash" -> replay(values,true);
      case "replay-recover" -> replay(values,false);
      default -> throw new IllegalStateException("Unapproved consumer acceptance mode");
    }
  }
}
