import React from 'react';
import {
  View,
  Text,
  ImageBackground,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../App';
import Icon from 'react-native-vector-icons/Ionicons';

type Props = NativeStackScreenProps<RootStackParamList, 'ROOST'>;

const HomeScreen: React.FC<Props> = ({ navigation }) => {
  const pins = [
    { id: 1, top: '82%', left: '30%', name: 'Babbio \n Garage' },
    { id: 2, top: '67%', left: '80%', name: 'River Lot' },
    { id: 3, top: '30%', left: '25%', name: '8th St Lot' },
    { id: 4, top: '16%', left: '70%', name: 'North \n Lot' },
    { id: 5, top: '1%', left: '82%', name: 'Castle Point \n Hall Lot' },
    { id: 6, top: '32%', left: '89%', name: 'Howe \n Center \n Lot' },
  ];

  return (
    <ImageBackground
      source={require('../other/stevensmap.jpg')}
      resizeMode="contain"
      style={styles.background}
    >
      <View style={styles.container}>
        {pins.map(pin => (
          <TouchableOpacity
            key={pin.id}
            style={[styles.marker, { top: pin.top as any, left: pin.left as any }]}
            onPress={() => navigation.navigate('AvailableParkingSpaces')}
          >
            <Icon name="location-sharp" size={30} color="red" />
            <View style={styles.pinBubble}>
              <Text style={styles.pinBubbleText}>{pin.name}</Text>
            </View>
          </TouchableOpacity>
        ))}
      </View>
    </ImageBackground>
  );
};

const styles = StyleSheet.create({
  background: {
    flex: 1,
    width: '100%',
    height: '100%',
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
  pinBubble: {
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    marginTop: 2,
  },
  pinBubbleText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
    // subtle outline for extra legibility
    textShadowColor: 'rgba(0,0,0,0.9)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
});

export default HomeScreen;
