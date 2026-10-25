import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.common.*;

/** Independent broker-side observer; does not infer Kafka membership from Pods. */
public class Chapter018 {
  static void check(boolean ok, String message) {
    if (!ok) throw new IllegalStateException(message);
  }
  public static void main(String[] args) throws Exception {
    String topic=args[0], group=args[1];
    int count=Integer.parseInt(args[2]);
    Properties p=new Properties();
    p.put("bootstrap.servers", "qa-kafka-ha-kafka-bootstrap:9092");
    p.put("default.api.timeout.ms", "20000");
    p.put("request.timeout.ms", "10000");
    try(Admin admin=Admin.create(p)) {
      TopicDescription td=admin.describeTopics(List.of(topic)).allTopicNames().get(25,TimeUnit.SECONDS).get(topic);
      check(td.partitions().size()==3,"Expected three partitions");
      for(TopicPartitionInfo part:td.partitions())
        check(part.leader()!=null && part.leader().id()>=0 && part.replicas().size()==3 && part.isr().size()==3,
              "Degraded partition: "+part);
      ConsumerGroupDescription gd=admin.describeConsumerGroups(List.of(group)).all().get(25,TimeUnit.SECONDS).get(group);
      check(gd.state().toString().equalsIgnoreCase("stable"),"Unstable group: "+gd.state());
      check(gd.members().size()==count,"Member count: "+gd.members().size());
      Set<TopicPartition> all=new HashSet<>();
      int idle=0;
      for(MemberDescription member:gd.members()) {
        Set<TopicPartition> assigned=member.assignment().topicPartitions();
        if(assigned.isEmpty()) idle++;
        for(TopicPartition tp:assigned)
          check(tp.topic().equals(topic) && all.add(tp),"Overlapping or unexpected assignment");
        System.out.println("MEMBER:"+member.clientId()+":"+assigned);
      }
      check(all.size()==3,"Incomplete assignment");
      check(count!=2 || idle==0,"Idle member in two-member group");
      check(count!=4 || idle==1,"Expected exactly one idle member");
      System.out.println("ASSIGNMENT_OK");
    }
  }
}
