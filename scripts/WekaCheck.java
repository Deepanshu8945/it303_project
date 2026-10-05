import java.io.BufferedReader;
import java.io.FileReader;
import java.nio.charset.StandardCharsets;
import weka.core.Instances;

class WekaCheck {
    public static void main(String[] args) throws Exception {
        for (String path : args) {
            try (BufferedReader reader = new BufferedReader(new FileReader(path, StandardCharsets.UTF_8))) {
                Instances data = new Instances(reader);
                System.out.println(path + ": " + data.numInstances() + " instances, " + data.numAttributes() + " attributes");
            }
        }
    }
}
