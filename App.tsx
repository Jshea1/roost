import React from 'react';
import { SafeAreaView, Text, StyleSheet, View } from 'react-native';

function App(): React.JSX.Element {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.row}>
        <View style={styles.box}>
          <Text style={styles.boxText}>Space 1</Text>
        </View>
        <View style={styles.box}>
          <Text style={styles.boxText}>Space 2</Text>
        </View>
      </View>
      <View style={styles.row}>
        <View style={styles.box}>
          <Text style={styles.boxText}>Space 3</Text>
        </View>
        <View style={styles.box}>
          <Text style={styles.boxText}>Space 4</Text>
        </View>
      </View>
      <View style={styles.row}>
        <View style={styles.box}>
          <Text style={styles.boxText}>Space 5</Text>
        </View>
        <View style={styles.box}>
          <Text style={styles.boxText}>Space 6</Text>
        </View>
      </View>
      <View style={styles.row}>
        <View style={styles.box}>
          <Text style={styles.boxText}>Space 7</Text>
        </View>
        <View style={styles.box}>
          <Text style={styles.boxText}>Space 8</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f0f0f0',
  },
  row: {
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    marginBottom: 20, 
  },
  box: {
    width: 125, 
    height: 125, 
    backgroundColor: '#4CAF50',
    justifyContent: 'center', 
    alignItems: 'center', 
    marginHorizontal: 10, 
  },
  boxText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
});

export default App;
