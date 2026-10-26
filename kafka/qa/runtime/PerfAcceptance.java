import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.security.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.config.ConfigException;
import org.apache.kafka.common.*;
import org.apache.kafka.common.utils.AppInfoParser;

/** Bounded native Kafka performance tools; credentials never leave the restricted Pod. */
public class PerfAcceptance {
  static String bootstrap,user,topic,group,trial;static int records,size,rate,healthSamples,partitions=3,linger=0,batch=16384;
  static String compression="none",payloadMode="native-random";
  static void check(boolean value,String message) {if(!value)throw new IllegalStateException(message);}
  static void pass(String name) {System.out.println("CHECK:"+trial+"_"+name+":PASS");}
  static String escape(String value) {return value.replace("\\","\\\\").replace("\"","\\\"");}
  static Properties security() throws Exception {
    Path secret=Path.of("/identity/password");Set<PosixFilePermission> mode=Files.getPosixFilePermissions(secret);
    check(!mode.contains(PosixFilePermission.OTHERS_READ) && !mode.contains(PosixFilePermission.OTHERS_WRITE),"Credential file world accessible");
    Properties p=new Properties();p.put("bootstrap.servers",bootstrap);p.put("security.protocol","SASL_SSL");p.put("sasl.mechanism","SCRAM-SHA-512");
    p.put("ssl.endpoint.identification.algorithm","https");p.put("ssl.truststore.type","PEM");p.put("ssl.truststore.certificates",Files.readString(Path.of("/trust/ca.crt")));
    p.put("sasl.jaas.config","org.apache.kafka.common.security.scram.ScramLoginModule required username=\""+escape(user)+"\" password=\""+escape(Files.readString(secret).trim())+"\";");
    p.put("request.timeout.ms","8000");p.put("default.api.timeout.ms","12000");return p;
  }
  static void health(Admin admin) throws Exception {
    TopicDescription current=admin.describeTopics(List.of(topic)).allTopicNames().get(15,TimeUnit.SECONDS).get(topic);
    check(current.partitions().size()==partitions,"Unexpected partition count");
    for(TopicPartitionInfo partition:current.partitions())check(partition.leader()!=null && partition.leader().id()>=0 && partition.replicas().size()==3 && partition.isr().size()==3,"ABORT: missing leader, RF3 or full ISR");
    QuorumInfo quorum=admin.describeMetadataQuorum().quorumInfo().get(15,TimeUnit.SECONDS);
    check(quorum.leaderId()>=0 && quorum.voters().size()==3 && quorum.highWatermark()>=0,"ABORT: KRaft quorum unhealthy");healthSamples++;
  }
  static void stop(Process process) {process.descendants().forEach(child->child.destroyForcibly());process.destroyForcibly();}
  static String execute(Admin admin,Path logging,int timeout,String... command) throws Exception {
    ProcessBuilder builder=new ProcessBuilder(command).redirectErrorStream(true);
    builder.environment().put("KAFKA_HEAP_OPTS","-Xms64m -Xmx128m");
    builder.environment().put("LOG_DIR",logging.getParent().toString());
    builder.environment().put("KAFKA_LOG4J_OPTS","-Dlog4j2.configurationFile="+logging);
    System.out.println("OBS:NATIVE_COMMAND:"+String.join(" ",command));
    Process process=builder.start();ExecutorService reader=Executors.newSingleThreadExecutor();ByteArrayOutputStream output=new ByteArrayOutputStream();
    Future<?> drain=reader.submit(()->{try {process.getInputStream().transferTo(output);}catch(IOException e) {throw new UncheckedIOException(e);}});
    long deadline=System.nanoTime()+Duration.ofSeconds(timeout).toNanos();boolean reported=false;
    try {
      while(!process.waitFor(1,TimeUnit.SECONDS)) {
        try {health(admin);}catch(Exception e) {stop(process);System.out.println("OBS:BENCHMARK_ABORT:KAFKA_HEALTH:"+e.getClass().getSimpleName());throw e;}
        if(System.nanoTime()>deadline) {stop(process);throw new IllegalStateException("Native benchmark exceeded bounded deadline");}
      }
      drain.get(10,TimeUnit.SECONDS);String text=output.toString(java.nio.charset.StandardCharsets.UTF_8);
      System.out.println("RAW_TOOL_BEGIN:"+Path.of(command[0]).getFileName());System.out.print(text);System.out.println("RAW_TOOL_END");reported=true;System.out.println("OBS:NATIVE_EXIT_CODE:"+Path.of(command[0]).getFileName()+":"+process.exitValue());
      boolean help=Arrays.asList(command).contains("--help");
      if(help) {
        boolean producer=command[0].endsWith("kafka-producer-perf-test.sh");
        check((process.exitValue()==0 || process.exitValue()==1) && text.contains(producer ? "--producer.config" : "--consumer.config")
          && text.contains(producer ? "--throughput" : "--messages") && text.contains("--topic") && !text.contains("Permission denied"),"Native tool help did not establish supported flags");
      } else check(process.exitValue()==0,"Native performance tool nonzero exit");
      health(admin);return text;
    } finally {
      if(process.isAlive())stop(process);
      if(!reported) {try {drain.get(5,TimeUnit.SECONDS);}catch(Exception ignored) {}System.out.println("RAW_FAILED_TOOL_OUTPUT");System.out.print(output.toString(java.nio.charset.StandardCharsets.UTF_8));}
      reader.shutdownNow();
    }
  }
  static void writeConfig(Path path,Properties properties) throws Exception {
    Files.createFile(path,PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")));
    try(OutputStream output=Files.newOutputStream(path)) {properties.store(output,"Restricted runtime configuration; never upload");}
    check(Files.getPosixFilePermissions(path).equals(PosixFilePermissions.fromString("rw-------")),"Temporary credential configuration mode drift");
  }
  static String digest(byte[] value) throws Exception {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value));}
  static void audit(Admin admin) throws Exception {
    List<TopicPartition> partitions=java.util.stream.IntStream.range(0,PerfAcceptance.partitions).mapToObj(i->new TopicPartition(topic,i)).toList();
    Map<TopicPartition,OffsetSpec> requests=new HashMap<>();for(TopicPartition partition:partitions)requests.put(partition,OffsetSpec.latest());
    Map<TopicPartition,ListOffsetsResult.ListOffsetsResultInfo> end=admin.listOffsets(requests).all().get(15,TimeUnit.SECONDS);
    check(end.values().stream().mapToLong(ListOffsetsResult.ListOffsetsResultInfo::offset).sum()==records,"Native acknowledgment count differs from total log end offsets");
    Map<String,Integer> expected=new HashMap<>();SplittableRandom random=new SplittableRandom(0);byte[] payload=new byte[size];
    for(int i=0;i<records;i++) {
      if(payloadMode.equals("native-random"))for(int j=0;j<size;j++)payload[j]=(byte)(random.nextInt(26)+65);
      else payload=compressiblePayload(random.nextInt(1200));
      expected.merge(digest(payload),1,Integer::sum);
    }
    Properties cp=security();cp.put("key.deserializer","org.apache.kafka.common.serialization.ByteArrayDeserializer");cp.put("value.deserializer","org.apache.kafka.common.serialization.ByteArrayDeserializer");
    cp.put("group.id",group);cp.put("enable.auto.commit","false");cp.put("auto.offset.reset","earliest");
    try(KafkaConsumer<byte[],byte[]> consumer=new KafkaConsumer<>(cp)) {
      consumer.assign(partitions);consumer.seekToBeginning(partitions);int received=0;long bytes=0;long deadline=System.nanoTime()+Duration.ofSeconds(60).toNanos();
      while(received<records && System.nanoTime()<deadline) {
        for(ConsumerRecord<byte[],byte[]> record:consumer.poll(Duration.ofMillis(300))) {
          check(record.key()==null && record.value()!=null && record.value().length==size,"Native payload key/size mismatch");String hash=digest(record.value());
          Integer remaining=expected.get(hash);check(remaining!=null && remaining>0,"Unexpected or duplicate native deterministic payload");
          if(remaining==1)expected.remove(hash);else expected.put(hash,remaining-1);received++;bytes+=record.value().length;
        }health(admin);
      }
      check(received==records && bytes==(long)records*size && expected.isEmpty(),"Native producer deterministic payload reconciliation incomplete");
      Map<TopicPartition,OffsetAndMetadata> offsets=new HashMap<>();
      for(TopicPartition partition:partitions) {check(consumer.position(partition)==end.get(partition).offset(),"Audit position did not reach captured end");offsets.put(partition,new OffsetAndMetadata(end.get(partition).offset()));}
      consumer.commitSync(offsets,Duration.ofSeconds(15));Map<TopicPartition,OffsetAndMetadata> committed=consumer.committed(new HashSet<>(partitions),Duration.ofSeconds(15));
      for(TopicPartition partition:partitions)check(committed.get(partition)!=null && committed.get(partition).offset()==end.get(partition).offset(),"Audit committed offset not at captured end");
      Map<TopicPartition,Long> captured=new TreeMap<>(Comparator.comparing(TopicPartition::toString));for(TopicPartition partition:partitions)captured.put(partition,end.get(partition).offset());
      System.out.println("OBS:PERF_AUDIT:records="+received+":bytes="+bytes+":zero_lag_against_captured_ends=true:partition_ends="+captured);
    }pass("native_payload_multiset_and_committed_catchup_exact");
  }
  static void resourceSnapshot(String when) {
    for(String name:List.of("cpu.stat","memory.current","memory.peak"))try {
      System.out.println("OBS:CLIENT_CGROUP:"+when+":"+name+":"+Files.readString(Path.of("/sys/fs/cgroup/"+name)).trim().replace('\n',';'));
    }catch(IOException e) {System.out.println("OBS:CLIENT_CGROUP:"+when+":"+name+":NOT_AVAILABLE");}
  }
  static Properties orderingProperties(int inflight) throws Exception {
    Properties p=security();p.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");p.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");
    p.put("acks","all");p.put("enable.idempotence","true");p.put("max.in.flight.requests.per.connection",Integer.toString(inflight));
    p.put("request.timeout.ms","8000");p.put("delivery.timeout.ms","30000");p.put("max.block.ms","15000");p.put("linger.ms","0");return p;
  }
  static double percentile(double[] samples,double quantile) {
    double[] sorted=samples.clone();Arrays.sort(sorted);return sorted[Math.max(0,(int)Math.ceil(quantile*sorted.length)-1)];
  }
  static void keyedSequence(Admin admin,String ownTopic,int inflight) throws Exception {
    topic=ownTopic;health(admin);TopicPartition partition=new TopicPartition(topic,0);
    long start=admin.listOffsets(Map.of(partition,OffsetSpec.latest())).all().get(15,TimeUnit.SECONDS).get(partition).offset();
    double[] callbacks=new double[30],enqueue=new double[30];java.util.concurrent.atomic.AtomicInteger success=new java.util.concurrent.atomic.AtomicInteger(),failures=new java.util.concurrent.atomic.AtomicInteger();
    try(KafkaProducer<String,String> producer=new KafkaProducer<>(orderingProperties(inflight))) {
      List<Future<RecordMetadata>> pending=new ArrayList<>();
      for(int i=0;i<30;i++) {
        int id=i;long before=System.nanoTime();
        pending.add(producer.send(new ProducerRecord<>(topic,0,"ordering-key",user+"-inflight"+inflight+"-"+id),(metadata,error)->{
          callbacks[id]=(System.nanoTime()-before)/1e6;if(error==null)success.incrementAndGet();else failures.incrementAndGet();
        }));enqueue[i]=(System.nanoTime()-before)/1e6;
      }
      producer.flush();for(int i=0;i<pending.size();i++)check(pending.get(i).get(35,TimeUnit.SECONDS).offset()==start+i,"Unexpected acknowledged partition sequence");
      check(success.get()==30 && failures.get()==0,"Producer callback outcomes incomplete");
      System.out.println("OBS:ORDERING_CALLBACKS:inflight="+inflight+":attempts=30:success="+success+":failures="+failures+":p50_ms="+percentile(callbacks,.5)+":p95_ms="+percentile(callbacks,.95)+":p99_ms="+percentile(callbacks,.99)+":maximum_enqueue_ms="+percentile(enqueue,1.0)+":nearest_rank_per_run_samples=30");
    }
    Properties cp=security();cp.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");cp.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");cp.put("group.id",group);cp.put("enable.auto.commit","false");
    try(KafkaConsumer<String,String> consumer=new KafkaConsumer<>(cp)) {
      consumer.assign(List.of(partition));consumer.seek(partition,start);int next=0;long deadline=System.nanoTime()+Duration.ofSeconds(45).toNanos();
      while(next<30 && System.nanoTime()<deadline) {
        for(ConsumerRecord<String,String> record:consumer.poll(Duration.ofMillis(300))) {
          check(record.partition()==0 && record.offset()==start+next && record.key().equals("ordering-key") && record.value().equals(user+"-inflight"+inflight+"-"+next),"Partition-local keyed sequence gap, duplicate, value or order mismatch");next++;
        }health(admin);
      }
      check(next==30 && consumer.position(partition)==start+30,"Keyed sequence incomplete");
      long end=admin.listOffsets(Map.of(partition,OffsetSpec.latest())).all().get(15,TimeUnit.SECONDS).get(partition).offset();
      check(end==start+30,"Unexpected additional records in keyed partition");consumer.commitSync(Map.of(partition,new OffsetAndMetadata(end)),Duration.ofSeconds(15));
      check(consumer.committed(Set.of(partition),Duration.ofSeconds(15)).get(partition).offset()==end,"Keyed sequence committed offset mismatch");
      System.out.println("OBS:KEYED_ORDERING:inflight="+inflight+":start="+start+":end="+end+":records=30:partition=0:scope=healthy_session_no_ack_loss_injected");
    }pass("keyed_ordering_commits_max_inflight_"+inflight);
  }
  static void correctness(String[] args) throws Exception {
    check(args.length==6,"Expected approved producer correctness arguments");check(AppInfoParser.getVersion().equals("4.0.0"),"Unexpected producer correctness client version");bootstrap=args[0];user=args[1];group=args[4];trial="producer-correctness";partitions=6;topic=args[2];int badPort=Integer.parseInt(args[5]);
    check(badPort==19095,"Unapproved client-only metadata failure endpoint");resourceSnapshot("before");
    try(Admin admin=Admin.create(security())) {
      health(admin);boolean invalid=false;
      try(KafkaProducer<String,String> unsupported=new KafkaProducer<>(orderingProperties(6))) {unsupported.close(Duration.ofSeconds(1));}
      catch(ConfigException expected) {invalid=true;}
      check(invalid,"Unsupported idempotent max.in.flight combination was not rejected");pass("unsupported_idempotent_inflight_rejected_before_traffic");
      Properties wrong=orderingProperties(5);java.net.URI endpoint=java.net.URI.create("ssl://"+bootstrap);
      wrong.put("bootstrap.servers",endpoint.getHost()+":"+badPort);wrong.put("max.block.ms","2000");wrong.put("request.timeout.ms","1000");wrong.put("delivery.timeout.ms","3000");wrong.put("retry.backoff.ms","100");
      KafkaProducer<String,String> blocked=new KafkaProducer<>(wrong);boolean metadataTimeout=false;long started=System.nanoTime();double elapsed;
      try {
        try {blocked.send(new ProducerRecord<>(topic,0,"ordering-key","must-not-enqueue"));}
        catch(org.apache.kafka.common.errors.TimeoutException expected) {metadataTimeout=true;}
        elapsed=(System.nanoTime()-started)/1e9;check(metadataTimeout && elapsed<=10.0,"Unreachable bootstrap did not produce a bounded synchronous metadata max.block timeout");
        System.out.println("OBS:PRODUCER_TIMEOUT:class=METADATA_MAX_BLOCK:outcome=NOT_ENQUEUED:seconds="+elapsed+":max_block_ms=2000:acceptance_budget_seconds=10:queued_delivery_timeout_not_proven");
      } finally {blocked.close(Duration.ofSeconds(1));}
      pass("unreachable_metadata_max_block_classified_not_enqueued");
      keyedSequence(admin,args[2],1);keyedSequence(admin,args[3],5);health(admin);resourceSnapshot("after");
      System.out.println("OBS:IDEMPOTENCE_BOUNDARY:wire_ack_loss_retry_deduplication=NOT_EXECUTED:external_business_exactly_once=NOT_CLAIMED");pass("secure_producer_recovery_full_isr_and_quorum");
    }
  }
  static byte[] compressiblePayload(int id) {
    String header=String.format(Locale.ROOT,"synthetic-event-%06d|",id);return (header+"A".repeat(1024-header.length())).getBytes(java.nio.charset.StandardCharsets.UTF_8);
  }
  static String[] producerCommand(Path config,Path payload) {
    List<String> command=new ArrayList<>(List.of("/opt/kafka/bin/kafka-producer-perf-test.sh","--topic",topic,"--num-records",Integer.toString(records),"--throughput",Integer.toString(rate),"--producer.config",config.toString(),"--print-metrics"));
    if(payloadMode.equals("native-random"))command.addAll(List.of("--record-size",Integer.toString(size)));
    else command.addAll(List.of("--payload-file",payload.toString()));
    return command.toArray(String[]::new);
  }
  public static void main(String[] args) throws Exception {
    if(args.length>0 && args[0].equals("correctness")) {correctness(Arrays.copyOfRange(args,1,args.length));return;}
    check(args.length==8 || args.length==13,"Expected approved benchmark argument profile");
    if(args.length==13) {
      partitions=Integer.parseInt(args[8]);linger=Integer.parseInt(args[9]);batch=Integer.parseInt(args[10]);compression=args[11];payloadMode=args[12];
      check(Set.of(3,6).contains(partitions) && Set.of(0,5,20).contains(linger) && Set.of(16384,65536,131072).contains(batch)
        && Set.of("none","lz4","zstd","snappy","gzip").contains(compression) && Set.of("native-random","compressible-set").contains(payloadMode),"Unapproved producer experiment profile");
    }

    bootstrap=args[0];user=args[1];topic=args[2];group=args[3];trial=args[4];records=Integer.parseInt(args[5]);size=Integer.parseInt(args[6]);rate=Integer.parseInt(args[7]);
    check(records>0 && records<=1200 && size==1024 && rate>=1 && rate<=800,"Unapproved benchmark payload/rate budget");
    check(AppInfoParser.getVersion().equals("4.0.0"),"Unexpected native client version");System.out.println("OBS:KAFKA_CLIENT_VERSION:"+AppInfoParser.getVersion());
    for(String tool:List.of("kafka-producer-perf-test.sh","kafka-consumer-perf-test.sh"))check(Files.isExecutable(Path.of("/opt/kafka/bin/"+tool)),"Required native Kafka tool missing");
    Path directory=Files.createTempDirectory("restricted-perf-",PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
    Path producer=directory.resolve("producer.properties"),consumer=directory.resolve("consumer.properties"),logging=directory.resolve("logging.xml"),payloadFile=directory.resolve("synthetic-payloads.txt");
    try(Admin admin=Admin.create(security())) {
      health(admin);Properties pp=security();pp.put("acks","all");pp.put("enable.idempotence","true");pp.put("compression.type",compression);pp.put("linger.ms",Integer.toString(linger));pp.put("batch.size",Integer.toString(batch));pp.put("max.in.flight.requests.per.connection","5");
      pp.put("delivery.timeout.ms","30000");pp.put("max.block.ms","15000");
      Properties cp=security();cp.put("enable.auto.commit","false");writeConfig(producer,pp);writeConfig(consumer,cp);
      Files.writeString(logging,"<Configuration status=\"ERROR\"><Appenders><Console name=\"Console\" target=\"SYSTEM_ERR\"><PatternLayout pattern=\"%level %message%n\"/></Console></Appenders><Loggers><Root level=\"warn\"><AppenderRef ref=\"Console\"/></Root></Loggers></Configuration>");
      if(payloadMode.equals("compressible-set")) {
        StringBuilder data=new StringBuilder();for(int i=0;i<1200;i++)data.append(new String(compressiblePayload(i),java.nio.charset.StandardCharsets.UTF_8)).append('\n');
        Files.writeString(payloadFile,data);System.out.println("OBS:CONTROLLED_PAYLOAD_DATASET_SHA256:"+digest(Files.readAllBytes(payloadFile))+":records=1200:bytes_each=1024:compressible_synthetic_not_real_application");
      }
      System.out.println("OBS:PRODUCER_PROFILE:partitions="+partitions+":linger="+linger+":batch="+batch+":compression="+compression+":payload="+payloadMode+":acks=all:idempotence=true:max_inflight=5");
      resourceSnapshot("before");
      if(trial.equals("warmup")) {
        execute(admin,logging,30,"/opt/kafka/bin/kafka-producer-perf-test.sh","--help");
        execute(admin,logging,30,"/opt/kafka/bin/kafka-consumer-perf-test.sh","--help");
      }
      long started=System.nanoTime();
      execute(admin,logging,90,producerCommand(producer,payloadFile));
      pass("native_producer_process_completed_acks_all_idempotent");
      execute(admin,logging,60,"/opt/kafka/bin/kafka-consumer-perf-test.sh","--bootstrap-server",bootstrap,"--topic",topic,"--messages",Integer.toString(records),"--group",group,"--timeout","30000","--consumer.config",consumer.toString());
      pass("native_consumer_process_completed");audit(admin);resourceSnapshot("after");health(admin);
      System.out.println("OBS:PERF_TRIAL_COMPLETION_SECONDS:"+(System.nanoTime()-started)/1e9+":health_samples="+healthSamples+":NOT_PRODUCTION_CAPACITY");pass("full_isr_quorum_polling_and_final_health");
    } finally {
      Files.deleteIfExists(producer);Files.deleteIfExists(consumer);Files.deleteIfExists(logging);Files.deleteIfExists(payloadFile);Files.deleteIfExists(directory);
    }
  }
}
