import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.common.config.ConfigResource;

/** Supported native load with actual per-broker JMX samples and effective configuration. */
public class BrokerAcceptance {
  static String quote(String text) {return "\""+text.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";}
  static void effective(int expected) throws Exception {
    try(Admin admin=Admin.create(PerfAcceptance.security())) {
      PerfAcceptance.health(admin);
      Collection<org.apache.kafka.common.Node> nodes=admin.describeCluster().nodes().get(15,TimeUnit.SECONDS);
      PerfAcceptance.check(nodes.size()==3,"Expected three live brokers");
      List<ConfigResource> resources=nodes.stream().map(node->new ConfigResource(ConfigResource.Type.BROKER,Integer.toString(node.id()))).toList();
      Map<ConfigResource,Config> configs=admin.describeConfigs(resources).all().get(15,TimeUnit.SECONDS);
      List<String> observed=new ArrayList<>();
      for(var entry:configs.entrySet()) {
        ConfigEntry value=entry.getValue().get("num.io.threads");
        PerfAcceptance.check(value!=null && !value.isReadOnly() && value.value().equals(Integer.toString(expected)),"Effective broker IO configuration differs from approved value");
        observed.add("{\"broker\":"+quote(entry.getKey().name())+",\"io_threads\":"+value.value()+",\"source\":"+quote(value.source().toString())+"}");
      }
      System.out.println("OBS:EFFECTIVE_IO_CONFIG:["+String.join(",",observed)+"]");
    }
  }
  static class Scraper {
    final String[] hosts;final HttpClient client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    final Queue<Throwable> failures=new ConcurrentLinkedQueue<>();final ScheduledExecutorService scheduler=Executors.newSingleThreadScheduledExecutor();
    int sequence=0;
    Scraper(String targets) {
      hosts=targets.split(",");PerfAcceptance.check(hosts.length==3,"Expected exact broker metrics targets");
      for(int i=0;i<3;i++)PerfAcceptance.check(hosts[i].equals("qa-kafka-ha-dual-role-"+i+".qa-kafka-ha-kafka-brokers.kafka-qa.svc:9404"),"Unapproved metrics target");
    }
    void capture(String phase) throws Exception {
      int sample=sequence++;PerfAcceptance.check(sample<160,"Metrics sample budget exceeded");
      for(int i=0;i<hosts.length;i++) {
        HttpRequest request=HttpRequest.newBuilder(URI.create("http://"+hosts[i]+"/metrics")).timeout(Duration.ofSeconds(5)).GET().build();
        HttpResponse<String> response=client.send(request,HttpResponse.BodyHandlers.ofString());PerfAcceptance.check(response.statusCode()==200,"Metrics endpoint did not respond successfully");
        List<String> selected=response.body().lines().filter(line->line.startsWith("qa_") || line.startsWith("jvm_memory_bytes_") || line.startsWith("jvm_gc_collection_seconds_")).toList();
        PerfAcceptance.check(!selected.isEmpty(),"Selected broker metrics missing");
        System.out.println("OBS:BROKER_SAMPLE:{\"broker\":"+i+",\"sequence\":"+sample+",\"phase\":"+quote(phase)+",\"timestamp_utc\":"+quote(java.time.Instant.now().toString())+",\"metrics\":["+String.join(",",selected.stream().map(BrokerAcceptance::quote).toList())+"]}");
      }
    }
    void start() throws Exception {
      capture("before");scheduler.scheduleWithFixedDelay(()->{try {capture("native_window");}catch(Throwable e) {failures.add(e);}},0,2,TimeUnit.SECONDS);
    }
    void finish() throws Exception {
      scheduler.shutdownNow();PerfAcceptance.check(scheduler.awaitTermination(12,TimeUnit.SECONDS),"Metrics sampler did not stop");
      // Interruption on intentional shutdown is allowed only at this explicit stop boundary.
      failures.removeIf(error->error instanceof InterruptedException);
      PerfAcceptance.check(failures.isEmpty(),"Broker instrumentation failed during load");capture("after");
    }
  }
  public static void main(String[] args) throws Exception {
    boolean verify=args.length>0 && args[0].equals("verify");
    if(verify) {
      PerfAcceptance.check(args.length==7,"Expected bounded rollback verification arguments");
      PerfAcceptance.bootstrap=args[1];PerfAcceptance.user=args[2];PerfAcceptance.topic=args[3];PerfAcceptance.group=args[4];PerfAcceptance.trial="restore";PerfAcceptance.partitions=6;
      PerfAcceptance.check(args[6].equals("8"),"Rollback must restore approved baseline");effective(8);
      new Scraper(args[5]).capture("rollback");PerfAcceptance.pass("effective_broker_config_full_isr_and_quorum");return;
    }
    PerfAcceptance.check(args.length==15,"Expected native profile plus instrumented broker setting");
    int expected=Integer.parseInt(args[14]);PerfAcceptance.check(expected==8 || expected==10,"Unapproved IO thread setting");
    PerfAcceptance.bootstrap=args[0];PerfAcceptance.user=args[1];PerfAcceptance.topic=args[2];PerfAcceptance.group=args[3];PerfAcceptance.trial=args[4];PerfAcceptance.partitions=6;
    effective(expected);Scraper scraper=new Scraper(args[13]);
    try {scraper.start();PerfAcceptance.main(Arrays.copyOf(args,13));}finally {scraper.finish();}
    effective(expected);PerfAcceptance.pass("per_broker_instrumentation_and_effective_io_configuration");
  }
}
