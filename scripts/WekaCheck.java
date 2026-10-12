import java.io.BufferedReader;
import java.io.FileReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import weka.core.Attribute;
import weka.core.Instance;
import weka.core.Instances;

class WekaCheck {
    private static String decode(String value) {
        return new String(Base64.getDecoder().decode(value), StandardCharsets.UTF_8);
    }

    private static void require(boolean condition) {
        if (!condition) throw new IllegalArgumentException("Output differs from reviewed dataset.");
    }

    private static void verify(String path, String expectedPath) throws Exception {
        try (BufferedReader reader = Files.newBufferedReader(Path.of(path), StandardCharsets.UTF_8);
             BufferedReader expected = Files.newBufferedReader(Path.of(expectedPath), StandardCharsets.UTF_8)) {
            Instances data = new Instances(reader);
            require(data.relationName().equals(decode(expected.readLine())));
            int columns = Integer.parseInt(expected.readLine());
            require(data.numAttributes() == columns);
            for (int col = 0; col < columns; col++) {
                String[] schema = expected.readLine().split("\t", -1);
                Attribute attribute = data.attribute(col);
                require(attribute.name().equals(decode(schema[0])));
                switch (schema[1]) {
                    case "numeric": require(attribute.isNumeric()); break;
                    case "string": require(attribute.isString()); break;
                    case "date":
                        require(attribute.isDate());
                        require(attribute.getDateFormat().equals(decode(schema[2])));
                        break;
                    case "nominal":
                        require(attribute.isNominal() && attribute.numValues() == schema.length - 3);
                        for (int v = 3; v < schema.length; v++)
                            require(attribute.value(v - 3).equals(decode(schema[v])));
                        break;
                    default: require(false);
                }
            }
            int rows = Integer.parseInt(expected.readLine());
            require(data.numInstances() == rows);
            for (int row = 0; row < rows; row++) {
                String[] values = expected.readLine().split("\t", -1);
                require(values.length == columns);
                Instance instance = data.instance(row);
                for (int col = 0; col < columns; col++) {
                    if (values[col].equals("N")) {
                        require(instance.isMissing(col));
                        continue;
                    }
                    require(!instance.isMissing(col));
                    String value = decode(values[col].substring(1));
                    Attribute attribute = data.attribute(col);
                    if (attribute.isDate()) {
                        require(instance.value(col) == attribute.parseDate(value));
                    } else if (attribute.isNumeric()) {
                        double number = Double.parseDouble(value);
                        require(Double.isFinite(number));
                        require(Double.doubleToLongBits(instance.value(col)) == Double.doubleToLongBits(number));
                    } else {
                        require(instance.stringValue(col).equals(value));
                    }
                }
            }
            require(expected.readLine() == null);
            System.out.println("VERIFIED\t" + rows + "\t" + columns);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 3 && args[0].equals("--verify")) {
            verify(args[1], args[2]);
            return;
        }
        for (String path : args) {
            try (BufferedReader reader = new BufferedReader(new FileReader(path, StandardCharsets.UTF_8))) {
                Instances data = new Instances(reader);
                System.out.println(path + ": " + data.numInstances() + " instances, " + data.numAttributes() + " attributes");
            }
        }
    }
}
