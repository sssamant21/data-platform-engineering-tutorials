import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.security.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.*;
import org.apache.kafka.common.utils.AppInfoParser;

/** Bounded native Kafka performance tools; credentials never leave the restricted Pod. */
public class PerfAcceptance {
  static String bootstrap,user,topic,group,trial;static int records,size,rate,healthSamples;
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
    check(current.partitions().size()==3,"Unexpected partition count");
    for(TopicPartitionInfo partition:current.partitions())check(partition.leader()!=null && partition.leader().id()>=0 && partition.replicas().size()==3 && partition.isr().size()==3,"ABORT: missing leader, RF3 or full ISR");
    QuorumInfo quorum=admin.describeMetadataQuorum().quorumInfo().get(15,TimeUnit.SECONDS);
    check(quorum.leaderId()>=0 && quorum.voters().size()==3 && quorum.highWatermark()>=0,"ABORT: KRaft quorum unhealthy");healthSamples++;
  }
  static void stop(Process process) {process.descendants().forEach(child->child.destroyForcibly());process.destroyForcibly();}
  static String execute(Admin admin,Path logging,int timeout,String... command) throws Exception {
    ProcessBuilder builder=new ProcessBuilder(command).redirectErrorStream(true);
    builder.environment().put("KAFKA_HEAP_OPTS","-Xms64m -Xmx128m");
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
      check(process.exitValue()==0,"Native performance tool nonzero exit");health(admin);return text;
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
    List<TopicPartition> partitions=List.of(new TopicPartition(topic,0),new TopicPartition(topic,1),new TopicPartition(topic,2));
    Map<TopicPartition,OffsetSpec> requests=new HashMap<>();for(TopicPartition partition:partitions)requests.put(partition,OffsetSpec.latest());
    Map<TopicPartition,ListOffsetsResult.ListOffsetsResultInfo> end=admin.listOffsets(requests).all().get(15,TimeUnit.SECONDS);
    check(end.values().stream().mapToLong(ListOffsetsResult.ListOffsetsResultInfo::offset).sum()==records,"Native acknowledgment count differs from total log end offsets");
    Map<String,Integer> expected=new HashMap<>();SplittableRandom random=new SplittableRandom(0);byte[] payload=new byte[size];
    for(int i=0;i<records;i++) {for(int j=0;j<size;j++)payload[j]=(byte)(random.nextInt(26)+65);expected.merge(digest(payload),1,Integer::sum);}
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
  public static void main(String[] args) throws Exception {
    bootstrap=args[0];user=args[1];topic=args[2];group=args[3];trial=args[4];records=Integer.parseInt(args[5]);size=Integer.parseInt(args[6]);rate=Integer.parseInt(args[7]);
    check(records>0 && records<=1200 && size==1024 && rate>=1 && rate<=800,"Unapproved benchmark payload/rate budget");
    check(AppInfoParser.getVersion().equals("4.0.0"),"Unexpected native client version");System.out.println("OBS:KAFKA_CLIENT_VERSION:"+AppInfoParser.getVersion());
    for(String tool:List.of("kafka-producer-perf-test.sh","kafka-consumer-perf-test.sh"))check(Files.isExecutable(Path.of("/opt/kafka/bin/"+tool)),"Required native Kafka tool missing");
    Path directory=Files.createTempDirectory("restricted-perf-",PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
    Path producer=directory.resolve("producer.properties"),consumer=directory.resolve("consumer.properties"),logging=directory.resolve("logging.xml");
    try(Admin admin=Admin.create(security())) {
      health(admin);Properties pp=security();pp.put("acks","all");pp.put("enable.idempotence","true");pp.put("compression.type","none");pp.put("linger.ms","0");pp.put("batch.size","16384");
      pp.put("delivery.timeout.ms","30000");pp.put("max.block.ms","15000");
      Properties cp=security();cp.put("enable.auto.commit","false");writeConfig(producer,pp);writeConfig(consumer,cp);
      Files.writeString(logging,"<Configuration status=\"ERROR\"><Appenders><Console name=\"Console\" target=\"SYSTEM_ERR\"><PatternLayout pattern=\"%level %message%n\"/></Console></Appenders><Loggers><Root level=\"warn\"><AppenderRef ref=\"Console\"/></Root></Loggers></Configuration>");
      resourceSnapshot("before");
      if(trial.equals("warmup")) {
        execute(admin,logging,30,"/opt/kafka/bin/kafka-producer-perf-test.sh","--help");
        execute(admin,logging,30,"/opt/kafka/bin/kafka-consumer-perf-test.sh","--help");
      }
      long started=System.nanoTime();
      execute(admin,logging,90,"/opt/kafka/bin/kafka-producer-perf-test.sh","--topic",topic,"--num-records",Integer.toString(records),"--record-size",Integer.toString(size),"--throughput",Integer.toString(rate),"--producer.config",producer.toString(),"--print-metrics");
      pass("native_producer_process_completed_acks_all_idempotent");
      execute(admin,logging,60,"/opt/kafka/bin/kafka-consumer-perf-test.sh","--bootstrap-server",bootstrap,"--topic",topic,"--messages",Integer.toString(records),"--group",group,"--timeout","30000","--consumer.config",consumer.toString());
      pass("native_consumer_process_completed");audit(admin);resourceSnapshot("after");health(admin);
      System.out.println("OBS:PERF_TRIAL_COMPLETION_SECONDS:"+(System.nanoTime()-started)/1e9+":health_samples="+healthSamples+":NOT_PRODUCTION_CAPACITY");pass("full_isr_quorum_polling_and_final_health");
    } finally {
      Files.deleteIfExists(producer);Files.deleteIfExists(consumer);Files.deleteIfExists(logging);Files.deleteIfExists(directory);
    }
  }
}
