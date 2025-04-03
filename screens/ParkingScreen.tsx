import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  ImageBackground,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { fetchGoogleSheetsData } from "../services/googleSheets";

const spotPositions = [
  { id: 47,  top: "19.5%",   left: "56.5%",  rotation: 0 },
  { id: 48,  top: "22%",     left: "56.5%",  rotation: 0 },
  { id: 49,  top: "24.63%",  left: "56.5%",  rotation: 0 },
  { id: 50,  top: "27.7%",   left: "56.5%",  rotation: 0 },
  { id: 52,  top: "30.2%",   left: "56.5%",  rotation: 0 },
  { id: 54,  top: "32.75%",  left: "56.5%",  rotation: 0 },
  { id: 56,  top: "35.25%",  left: "56.5%",  rotation: 0 },
  { id: 58,  top: "38.35%",  left: "56.5%",  rotation: 0 },
  { id: 80,  top: "41.4%",   left: "56.5%",  rotation: 0 },
  { id: 61,  top: "46.5%",   left: "56.5%",  rotation: 0 },
  { id: 62,  top: "48.95%",  left: "56.5%",  rotation: 0 },
  { id: 64,  top: "52%",     left: "56.5%",  rotation: 0 },
  { id: 66,  top: "54.65%",  left: "56.5%",  rotation: 0 },
  { id: 68,  top: "57.08%",  left: "56.5%",  rotation: 0 },
  { id: 70,  top: "59.6%",   left: "56.5%",  rotation: 0 },
  { id: 72,  top: "62.8%",   left: "56.5%",  rotation: 0 },
  { id: 74,  top: "65.3%",   left: "56.5%",  rotation: 0 },
  { id: 75,  top: "67.8%",   left: "56.5%",  rotation: 0 },
  { id: 76,  top: "70.3%",   left: "56.5%",  rotation: 0 },

  { id: 38,  top: "19.5%",   left: "2%",     rotation: 0 },
  { id: 37,  top: "22%",     left: "2%",     rotation: 0 },
  { id: 36,  top: "24.42%",  left: "2%",     rotation: 0 },
  { id: 35,  top: "27.7%",   left: "2%",     rotation: 0 },
  { id: 33,  top: "30.09%",  left: "2%",     rotation: 0 },
  { id: 29,  top: "35.25%",  left: "2%",     rotation: 0 },
  { id: 27,  top: "38.35%",  left: "2%",     rotation: 0 },
  { id: 26,  top: "41.4%",   left: "2%",     rotation: 0 },
  { id: 25,  top: "44%",     left: "2%",     rotation: 0 },
  { id: 24,  top: "46.5%",   left: "2%",     rotation: 0 },
  { id: 23,  top: "48.95%",  left: "2%",     rotation: 0 },
  { id: 21,  top: "52%",     left: "2%",     rotation: 0 },
  { id: 19,  top: "54.72%",  left: "2%",     rotation: 0 },
  { id: 17,  top: "57.15%",  left: "2%",     rotation: 0 },
  { id: 15,  top: "59.6%",   left: "2%",     rotation: 0 },
  { id: 14,  top: "62.8%",   left: "2%",     rotation: 0 },
  { id: 13,  top: "65.3%",   left: "2%",     rotation: 0 },
  { id: 12,  top: "67.74%",  left: "2%",     rotation: 0 },

  { id: 34,  top: "27.7%",   left: "23.75%", rotation: 0 },
  { id: 32,  top: "30.2%",   left: "23.75%", rotation: 0 },
  { id: 21,  top: "32.75%",  left: "23.75%", rotation: 0 },
  { id: 30,  top: "35.25%",  left: "23.75%", rotation: 0 },
  { id: 28,  top: "38.2%",   left: "23.75%", rotation: 0 },
  { id: 180, top: "41.4%",   left: "23.75%", rotation: 0 },
  { id: 178, top: "44%",     left: "23.75%", rotation: 0 },
  { id: 176, top: "46.5%",   left: "23.75%", rotation: 0 },
  { id: 174, top: "48.95%",  left: "23.75%", rotation: 0 },
  { id: 22,  top: "52%",     left: "23.75%", rotation: 0 },
  { id: 20,  top: "54.72%",  left: "23.75%", rotation: 0 },
  { id: 18,  top: "57.15%",  left: "23.75%", rotation: 0 },
  { id: 16,  top: "59.6%",   left: "23.75%", rotation: 0 },
  { id: 424, top: "62.7%",   left: "23.75%", rotation: 0 },

  { id: 51,  top: "27.7%",   left: "35%",    rotation: 0 },
  { id: 53,  top: "30.2%",   left: "35%",    rotation: 0 },
  { id: 55,  top: "32.75%",  left: "35%",    rotation: 0 },
  { id: 57,  top: "35.25%",  left: "35%",    rotation: 0 },
  { id: 59,  top: "38.2%",   left: "35%",    rotation: 0 },
  { id: 63,  top: "52%",     left: "35%",    rotation: 0 },
  { id: 65,  top: "54.72%",  left: "35%",    rotation: 0 },
  { id: 67,  top: "57.15%",  left: "35%",    rotation: 0 },
  { id: 69,  top: "59.6%",   left: "35%",    rotation: 0 },
  { id: 71,  top: "62.7%",   left: "35%",    rotation: 0 },
  { id: 73,  top: "65.23%",  left: "35%",    rotation: 0 },

  { id: 97,  top: "48.95%",  left: "67.5%",  rotation: 0 },
  { id: 95,  top: "52%",     left: "67.5%",  rotation: 0 },
  { id: 93,  top: "54.72%",  left: "67.5%",  rotation: 0 },
  { id: 91,  top: "57.15%",  left: "67.5%",  rotation: 0 },
  { id: 89,  top: "59.6%",   left: "67.5%",  rotation: 0 },
  { id: 87,  top: "62.8%",   left: "67.5%",  rotation: 0 },
  { id: 85,  top: "65.27%",  left: "67.5%",  rotation: 0 },
  { id: 83,  top: "67.8%",   left: "67.5%",  rotation: 0 },
  { id: 81,  top: "70.3%",   left: "67.5%",  rotation: 0 },

  { id: 94,  top: "52%",     left: "88%",    rotation: 0 },
  { id: 92,  top: "54.72%",  left: "88%",    rotation: 0 },
  { id: 90,  top: "57.15%",  left: "88%",    rotation: 0 },
  { id: 88,  top: "59.6%",   left: "88%",    rotation: 0 },
  { id: 86,  top: "62.8%",   left: "88%",    rotation: 0 },
  { id: 84,  top: "65.27%",  left: "88%",    rotation: 0 },
  { id: 82,  top: "67.8%",   left: "88%",    rotation: 0 },
  { id: 80,  top: "70.4%",   left: "88%",    rotation: 0 },
  { id: 79,  top: "73.5%",   left: "88%",    rotation: 0 },
  { id: 78,  top: "75.95%",  left: "88%",    rotation: 0 },
  { id: 77,  top: "78.5%",   left: "88%",    rotation: 0 },

  { id: 39,  top: "16%",     left: "10%",    rotation: 270 },
  { id: 40,  top: "16%",     left: "15%",    rotation: 270 },
  { id: 41,  top: "16%",     left: "19.8%",  rotation: 270 },
  { id: 42,  top: "16%",     left: "25.5%",  rotation: 270 },
  { id: 43,  top: "16%",     left: "30.25%", rotation: 270 },
  { id: 44,  top: "16%",     left: "39.4%",  rotation: 270 },
  { id: 45,  top: "16%",     left: "43.8%",  rotation: 270 },
  { id: 46,  top: "16%",     left: "48.7%",  rotation: 270 },

  { id: 11,  top: "71.8%",   left: "7.4%",   rotation: 290 },
  { id: 10,  top: "72.6%",   left: "11.8%",  rotation: 290 },
  { id: 9,   top: "73.4%",   left: "16.2%",  rotation: 290 },
  { id: 8,   top: "75.3%",   left: "25.3%",  rotation: 290 },
  { id: 7,   top: "76.1%",   left: "29.9%",  rotation: 290 },
  { id: 6,   top: "77.7%",   left: "37.8%",  rotation: 290 },
  { id: 5,   top: "78.5%",   left: "42.4%",  rotation: 290 },
  { id: 4,   top: "79.45%",  left: "47.1%",  rotation: 290 },
  { id: 3,   top: "80.3%",   left: "51.9%",  rotation: 290 },
  { id: 2,   top: "81.4%",   left: "57.2%",  rotation: 290 },
  { id: 1,   top: "82.2%",   left: "61.8%",  rotation: 290 },

  
];

const ParkingScreen: React.FC = () => {
  const [data, setData] = useState<string[][]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const loadData = async () => {
      const sheetData = await fetchGoogleSheetsData();
      if (sheetData) {
        console.log("Raw Sheet Data:", sheetData);
        const adjustedData = sheetData.slice(1);
        setData(adjustedData);
      }
      setLoading(false);
    };

    loadData();
    // Refresh every 5 seconds
    const interval = setInterval(loadData, 5000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#0000ff" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ImageBackground
        source={require("../other/garage.jpeg")}
        resizeMode="contain"
        style={styles.backgroundImage}
      >
        {spotPositions.map((spot) => {
          // row[0] = spot number, row[1] = occupancy (1 or 0)
          const occupancy =
            data[spot.id - 1] && data[spot.id - 1][1]
              ? data[spot.id - 1][1].trim()
              : "0";
          const isOccupied = occupancy === "1";

          return (
            <View
              key={spot.id}
              style={[
                styles.spotContainer,
                {
                  top: `${parseFloat(spot.top)}%`,
                  left: `${parseFloat(spot.left)}%`,
                  transform: [{ rotate: `${spot.rotation}deg` }],
                },
                isOccupied ? styles.occupied : styles.available,
              ]}
            >
              <Text style={styles.spotText}>{spot.id}</Text>
            </View>
          );
        })}
      </ImageBackground>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  backgroundImage: {
    flex: 1,
    width: "100%",
    height: "100%",
  },
  spotContainer: {
    position: "absolute",
    width: 42,
    height: 14,
    borderRadius: 5,
    justifyContent: "center",
    alignItems: "center",
  },
  spotText: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 10,
  },
  occupied: {
    backgroundColor: "rgba(255, 0, 0, 0.7)", // Red for taken spots
  },
  available: {
    backgroundColor: "rgba(0, 128, 0, 0.7)", // Green for available spots
  },
});

export default ParkingScreen;
