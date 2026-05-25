import { StyleSheet, Text, View } from "react-native";
import { colors, fonts } from "@smarttap/ui/tokens";

export default function HomeScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.eyebrow}>SMARTTAP</Text>
      <Text style={styles.title}>Mobile</Text>
      <Text style={styles.body}>Phase 2 launch. Structure ready.</Text>
      <Text style={styles.body}>Display font: {fonts.display}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.brand.green,
    padding: 24,
  },
  eyebrow: {
    color: colors.brand.amber,
    fontSize: 12,
    letterSpacing: 4,
    marginBottom: 12,
  },
  title: {
    color: colors.brand.offWhite,
    fontSize: 48,
  },
  body: {
    color: colors.brand.offWhite,
    fontSize: 16,
    opacity: 0.8,
    marginTop: 8,
  },
});
