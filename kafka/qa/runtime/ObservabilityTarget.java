import com.sun.net.httpserver.*;
import com.fasterxml.jackson.databind.*;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.*;

/** Internal synthetic target and separate local-only alert receiver; no external notifications. */
public class ObservabilityTarget {
  static final ObjectMapper JSON=new ObjectMapper();
  static final AtomicLong produced=new AtomicLong(),processed=new AtomicLong(),errors=new AtomicLong();
  static final AtomicBoolean exercised=new AtomicBoolean();
  static final AtomicReference<Map<String,Object>> proof=new AtomicReference<>();
  static final List<Map<String,Object>> receipts=new ArrayList<>();
  static String mode,owner,eventId;
  static void response(HttpExchange exchange,int status,Object value) throws Exception {
    byte[] body=ConsumerAcceptance.json(value).getBytes(StandardCharsets.UTF_8);exchange.getResponseHeaders().set("Content-Type","application/json");exchange.sendResponseHeaders(status,body.length);exchange.getResponseBody().write(body);exchange.close();
  }
  static Map<String,Object> exercise() throws Exception {
    PerfAcceptance.check(org.apache.kafka.common.utils.AppInfoParser.getVersion().equals("4.0.0"),"Unexpected canary client version");
    List<Double> acknowledgements=new ArrayList<>(),ages=new ArrayList<>();Set<Integer> ids=new TreeSet<>();
    try(Admin admin=Admin.create(PerfAcceptance.security())) {
      PerfAcceptance.health(admin);Map<TopicPartition,OffsetSpec> query=new HashMap<>();for(int i=0;i<3;i++)query.put(new TopicPartition(PerfAcceptance.topic,i),OffsetSpec.latest());
      var initial=admin.listOffsets(query).all().get(15,TimeUnit.SECONDS);PerfAcceptance.check(initial.values().stream().allMatch(offset->offset.offset()==0),"Canary topic must be fresh");
      try(KafkaProducer<String,String> producer=new KafkaProducer<>(ConsumerAcceptance.producer())) {
        for(int i=0;i<12;i++) {
          long start=System.nanoTime();RecordMetadata ack=producer.send(new ProducerRecord<>(PerfAcceptance.topic,i%3,System.currentTimeMillis(),"synthetic-key",ConsumerAcceptance.event(eventId,i))).get(35,TimeUnit.SECONDS);
          PerfAcceptance.check(ack.partition()==i%3 && ack.offset()==i/3,"Canary acknowledgment does not match exact partition/offset");produced.incrementAndGet();acknowledgements.add((System.nanoTime()-start)/1e6);
        }
      }
      try(KafkaConsumer<String,String> consumer=new KafkaConsumer<>(ConsumerAcceptance.consumer(owner+"-observability"))) {
        consumer.subscribe(List.of(PerfAcceptance.topic));long deadline=System.nanoTime()+Duration.ofSeconds(60).toNanos();
        while(ids.size()<12 && System.nanoTime()<deadline) {
          var batch=consumer.poll(Duration.ofMillis(200));Map<TopicPartition,OffsetAndMetadata> completed=new HashMap<>();
          for(ConsumerRecord<String,String> record:batch) {
            String[] values=record.value().split("\\|",3);int id=Integer.parseInt(values[1]);
            PerfAcceptance.check(id>=0 && id<12 && record.partition()==id%3 && record.key().equals("synthetic-key") && record.value().equals(ConsumerAcceptance.event(eventId,id)) && ids.add(id),"Canary event identity/value/partition/duplicate mismatch");
            PerfAcceptance.check(record.timestampType()==org.apache.kafka.common.record.TimestampType.CREATE_TIME && System.currentTimeMillis()>=record.timestamp(),"Canary timestamp source invalid");
            Thread.sleep(1);processed.incrementAndGet();ages.add((double)(System.currentTimeMillis()-record.timestamp()));completed.put(new TopicPartition(record.topic(),record.partition()),new OffsetAndMetadata(record.offset()+1));
          }
          if(!completed.isEmpty())consumer.commitSync(completed,Duration.ofSeconds(15));PerfAcceptance.health(admin);
        }
      }
      PerfAcceptance.check(ids.size()==12 && produced.get()==12 && processed.get()==12,"Canary application reconciliation incomplete");
      Map<TopicPartition,OffsetAndMetadata> committed=null;long commitDeadline=System.nanoTime()+Duration.ofSeconds(30).toNanos();
      while(System.nanoTime()<commitDeadline) {
        committed=admin.listConsumerGroupOffsets(PerfAcceptance.group).partitionsToOffsetAndMetadata().get(15,TimeUnit.SECONDS);
        boolean complete=true;for(int i=0;i<3;i++) {OffsetAndMetadata value=committed.get(new TopicPartition(PerfAcceptance.topic,i));if(value==null || value.offset()!=4)complete=false;}
        if(complete)break;PerfAcceptance.health(admin);Thread.sleep(100);
      }
      PerfAcceptance.check(committed!=null,"Canary committed-offset query did not complete");Map<String,Long> offsets=new TreeMap<>();for(int i=0;i<3;i++) {OffsetAndMetadata value=committed.get(new TopicPartition(PerfAcceptance.topic,i));PerfAcceptance.check(value!=null && value.offset()==4,"Canary commit not at captured end");offsets.put(Integer.toString(i),value.offset());}
      PerfAcceptance.health(admin);QuorumInfo quorum=admin.describeMetadataQuorum().quorumInfo().get(15,TimeUnit.SECONDS);
      Map<String,Object> result=new LinkedHashMap<>();result.put("produced",produced.get());result.put("processed",processed.get());result.put("committed_offsets",offsets);result.put("lag",0);result.put("leader_id",quorum.leaderId());result.put("voter_ids",quorum.voters().stream().map(voter->voter.replicaId()).sorted().toList());result.put("high_watermark",quorum.highWatermark());result.put("ack_wait_ms",ConsumerAcceptance.distribution(acknowledgements));result.put("created_to_processed_ms",ConsumerAcceptance.distribution(ages));result.put("verified_at_seconds",System.currentTimeMillis()/1000d);result.put("scope","synthetic processing and commit, not external business durability");return result;
    }
  }
  static boolean authorized(HttpExchange exchange) throws Exception {
    String supplied=exchange.getRequestHeaders().getFirst("X-QA-Token"),expected=Files.readString(Path.of("/qa-control/token")).trim();
    return supplied!=null && java.security.MessageDigest.isEqual(supplied.getBytes(StandardCharsets.UTF_8),expected.getBytes(StandardCharsets.UTF_8));
  }
  static Map<String,Object> quorum() throws Exception {
    try(Admin admin=Admin.create(PerfAcceptance.security())) {
      PerfAcceptance.health(admin);QuorumInfo value=admin.describeMetadataQuorum().quorumInfo().get(15,TimeUnit.SECONDS);
      return Map.of("leader_id",value.leaderId(),"voter_ids",value.voters().stream().map(voter->voter.replicaId()).sorted().toList(),"high_watermark",value.highWatermark(),"verified_at_seconds",System.currentTimeMillis()/1000d);
    }
  }
  static String metrics() {
    StringBuilder text=new StringBuilder("# TYPE qa_synthetic_target_value gauge\nqa_synthetic_target_value 1\n");
    text.append("# TYPE qa_client_produced_records_total counter\nqa_client_produced_records_total ").append(produced.get()).append('\n');
    text.append("# TYPE qa_client_processed_records_total counter\nqa_client_processed_records_total ").append(processed.get()).append('\n');
    text.append("# TYPE qa_client_errors_total counter\nqa_client_errors_total ").append(errors.get()).append('\n');
    Map<String,Object> measured=proof.get();
    if(measured!=null) {
      text.append("# TYPE qa_client_group_lag gauge\nqa_client_group_lag ").append(measured.get("lag")).append('\n');
      text.append("# TYPE qa_client_verified_timestamp_seconds gauge\nqa_client_verified_timestamp_seconds ").append(measured.get("verified_at_seconds")).append('\n');
      text.append("# TYPE qa_client_ack_wait_p99_ms gauge\nqa_client_ack_wait_p99_ms ").append(((Map<?,?>)measured.get("ack_wait_ms")).get("p99")).append('\n');
      text.append("# TYPE qa_client_event_age_p99_ms gauge\nqa_client_event_age_p99_ms ").append(((Map<?,?>)measured.get("created_to_processed_ms")).get("p99")).append('\n');
    }
    return text.toString();
  }
  static boolean receiverAuthorized(HttpExchange exchange) throws Exception {
    String supplied=exchange.getRequestHeaders().getFirst("Authorization"),expected="Bearer "+Files.readString(Path.of("/receiver-auth/token")).trim();
    return supplied!=null && java.security.MessageDigest.isEqual(supplied.getBytes(StandardCharsets.UTF_8),expected.getBytes(StandardCharsets.UTF_8));
  }
  static void receive(HttpExchange exchange) throws Exception {
    byte[] body=exchange.getRequestBody().readNBytes(65537);PerfAcceptance.check(body.length<=65536,"Synthetic notification too large");JsonNode value=JSON.readTree(body);
    PerfAcceptance.check(value.path("alerts").isArray() && value.path("alerts").size()>0 && value.path("alerts").size()<=16,"Invalid synthetic notification shape");
    List<Map<String,Object>> alerts=new ArrayList<>();
    for(JsonNode alert:value.path("alerts")) {
      String name=alert.path("labels").path("alertname").asText(),tag=alert.path("labels").path("qa_owner").asText(),status=alert.path("status").asText();
      PerfAcceptance.check(Set.of("KafkaQaSyntheticTargetDown","KafkaQaUnderMinISR","KafkaQaBrokerMetricsMissing","KafkaQaRequiredMetricMissing","KafkaQaKRaftSignalInvalid").contains(name) && tag.equals(owner) && Set.of("firing","resolved").contains(status),"Notification is not the owned synthetic alert");
      alerts.add(Map.of("alertname",name,"qa_owner",tag,"status",status,"starts_at",alert.path("startsAt").asText(),"ends_at",alert.path("endsAt").asText()));
    }
    synchronized(receipts) {if(receipts.size()==50)receipts.remove(0);receipts.add(Map.of("received_at_seconds",System.currentTimeMillis()/1000d,"status",value.path("status").asText(),"receiver",value.path("receiver").asText(),"alerts",alerts));}
    response(exchange,200,Map.of("accepted_synthetic_alerts",alerts.size()));
  }
  static void handle(HttpExchange exchange) {
    try {
      String path=exchange.getRequestURI().getPath(),method=exchange.getRequestMethod();
      if(path.equals("/healthz") && method.equals("GET")) {response(exchange,200,Map.of("mode",mode,"owner",owner));return;}
      if(mode.equals("receiver")) {
        if(!receiverAuthorized(exchange)) {response(exchange,403,Map.of("status","RECEIVER_AUTH_REQUIRED"));return;}
        if(path.equals("/alerts") && method.equals("POST")) {receive(exchange);return;}
        if(path.equals("/receipts") && method.equals("GET")) {synchronized(receipts) {response(exchange,200,new ArrayList<>(receipts));}return;}
      }else {
        if(mode.equals("target") && path.equals("/metrics") && method.equals("GET")) {byte[] body=metrics().getBytes(StandardCharsets.UTF_8);exchange.getResponseHeaders().set("Content-Type","text/plain; version=0.0.4");exchange.sendResponseHeaders(200,body.length);exchange.getResponseBody().write(body);exchange.close();return;}
        if(mode.equals("target") && path.equals("/proof") && method.equals("GET")) {Map<String,Object> value=proof.get();response(exchange,value==null ? 404 : 200,value==null ? Map.of("status","NOT_VERIFIED") : value);return;}
        if(path.equals("/quorum") && method.equals("GET")) {if(!authorized(exchange)) {response(exchange,403,Map.of("status","CONTROL_AUTH_REQUIRED"));return;}response(exchange,200,quorum());return;}
        if(mode.equals("target") && path.equals("/exercise") && method.equals("POST")) {
          if(!authorized(exchange)) {response(exchange,403,Map.of("status","CONTROL_AUTH_REQUIRED"));return;}
          if(!exercised.compareAndSet(false,true)) {response(exchange,409,Map.of("status","EXERCISE_ALREADY_ATTEMPTED"));return;}
          try {Map<String,Object> value=exercise();proof.set(value);response(exchange,200,value);}catch(Exception error) {errors.incrementAndGet();throw error;}return;
        }
      }
      response(exchange,404,Map.of("status","NOT_FOUND"));
    }catch(Exception error) {try {response(exchange,500,Map.of("error_class",error.getClass().getSimpleName()));}catch(Exception ignored) {exchange.close();}}
  }
  public static void main(String[] args) throws Exception {
    PerfAcceptance.check(args.length>=2,"Expected owned monitoring mode and identity");mode=args[0];owner=args[1];PerfAcceptance.check(owner.matches("ch036-[a-f0-9]{12}") && Set.of("target","receiver","probe").contains(mode),"Unapproved synthetic monitoring mode/owner");
    if(!mode.equals("receiver")) {PerfAcceptance.check(args.length==7,"Expected canary target configuration");PerfAcceptance.bootstrap=args[2];PerfAcceptance.user=args[3];PerfAcceptance.topic=args[4];PerfAcceptance.group=args[5];PerfAcceptance.trial="observability";PerfAcceptance.partitions=3;eventId=args[6];}
    else PerfAcceptance.check(args.length==2,"Receiver must not receive Kafka credentials");
    HttpServer server=HttpServer.create(new InetSocketAddress("0.0.0.0",8080),16);ExecutorService requests=Executors.newFixedThreadPool(4);server.setExecutor(requests);server.createContext("/",ObservabilityTarget::handle);server.start();
    Runtime.getRuntime().addShutdownHook(new Thread(()->{server.stop(1);requests.shutdownNow();}));
    Executors.newSingleThreadScheduledExecutor().schedule(()->System.exit(0),20,TimeUnit.MINUTES);
    System.out.println("CHECK:internal_synthetic_"+mode+"_ready:PASS");
  }
}
