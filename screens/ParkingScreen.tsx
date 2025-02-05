import React, { useEffect, useState } from "react";
import { View, Text, ScrollView, ActivityIndicator, StyleSheet } from "react-native";
import { fetchGoogleSheetsData } from "../services/googleSheets";

const GoogleSheetsScreen: React.FC = () => {
  const [data, setData] = useState<string[][]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const loadData = async () => {
      const sheetData = await fetchGoogleSheetsData();
      if (sheetData) setData(sheetData);
      setLoading(false);
    };

    loadData();
    const interval = setInterval(loadData, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <ScrollView style={styles.container}>
      {loading ? (
        <ActivityIndicator size="large" color="#0000ff" />
      ) : (
        <View>
          {data.length > 0 ? (
            data.map((row, index) => (
              <Text key={index} style={styles.rowText}>
                {row.join(" | ")}
              </Text>
            ))
          ) : (
            <Text>No data found</Text>
          )}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: 20 },
  rowText: { padding: 10, borderBottomWidth: 1 },
});

export default GoogleSheetsScreen;
