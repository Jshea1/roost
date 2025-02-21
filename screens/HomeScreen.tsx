import React from 'react';
import { View, Text, Button, StyleSheet, ImageBackground, TouchableOpacity, StyleProp, ViewStyle } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../App';
import Icon from 'react-native-vector-icons/Ionicons'; // Ensure typings are resolved

type Props = NativeStackScreenProps<RootStackParamList, 'ROOST'>;

const HomeScreen: React.FC<Props> = ({ navigation }) => {
  const pins = [
    { id: 1, top: '82%', left: '30%', name: 'Babbio \n Garage' },
    { id: 2, top: '67%', left: '80%', name: 'River Lot' },
    { id: 3, top: '30%', left: '25%', name: '8th St Lot' },
    { id: 4, top: '16%', left: '70%', name: 'North \n Lot' },
    { id: 5, top: '1%', left: '82%', name: 'Castle Point \n Hall Lot' },
    { id: 6, top: '30%', left: '91%', name: 'Howe \n Center \n Lot' },
  ];
   
  return (
    <ImageBackground 
      source={require('../other/stevensmap.jpg')} 
      style={styles.background}
    >
      <View style={styles.container}>
        <Button 
          title="View Available Parking Spaces" 
          onPress={() => navigation.navigate('AvailableParkingSpaces')} 
        />

        {/* Loop through pins */}
        {pins.map(pin => (
          <TouchableOpacity
            key={pin.id}
            style={[styles.marker, { top: pin.top as any, left: pin.left as any }]} 
            onPress={() => navigation.navigate('AvailableParkingSpaces')}
          >
            <Icon name="location-sharp" size={30} color="red" />
            <Text style={styles.pinLabel}>{pin.name}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </ImageBackground>
  );
};

const styles = StyleSheet.create({
  background: { 
    flex: 1, 
    resizeMode: "cover", 
  },
  container: { 
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center', 
  },
  marker: {
    position: 'absolute',
    alignItems: 'center',
  },
  pinLabel: {
    color: 'black',
    fontSize: 12,
    fontFamily: 'IBMPlexSans-Regular',
    marginTop: 2,
    textAlign: 'center',
  },
});

export default HomeScreen;
