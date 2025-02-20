import React from 'react';
import { View, Text, Button, StyleSheet, ImageBackground } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../App';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

const HomeScreen: React.FC<Props> = ({ navigation }) => {
  return (
    <ImageBackground 
      source={require('../other/stevensmap.jpg')} // 
      style={styles.background}
    >
      <View style={styles.container}>
        <Text style={styles.title}>ROOST APP</Text>
        <Button 
          title="View Available Parking Spaces" 
          onPress={() => navigation.navigate('AvailableParkingSpaces')} 
        />
      </View>
    </ImageBackground>
  );
};

const styles = StyleSheet.create({
  background: { 
    flex: 1, 
    resizeMode: "cover", 
    justifyContent: "center" 
  },
  container: { 
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center', 
  },
  title: { 
    fontSize: 64, 
    fontWeight: 'bold', 
    color: 'black', 
    marginBottom: 20 
  },
});

export default HomeScreen;
