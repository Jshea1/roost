import React, { useState } from 'react';
import {
  View,
  Text,
  ImageBackground,
  TouchableOpacity,
  StyleSheet,
  Modal,
  Linking,
  Platform,
  Alert,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../App';
import Icon from 'react-native-vector-icons/Ionicons';

type Props = NativeStackScreenProps<RootStackParamList, 'ROOST'>;

// 1) Define your coordinate lookup
const LOT_COORDINATES: Record<
  number,
  { label: string; lat: number; lng: number }
> = {
  1: { label: 'Babbio Garage',         lat: 40.74257, lng: -74.02608 },
  2: { label: 'River Lot',             lat: 40.74333, lng: -74.02477 },
  3: { label: '8th St Lot',            lat: 40.74552, lng: -74.02620 },
  4: { label: 'North Lot',             lat: 40.74645, lng: -74.02481 },
  5: { label: 'Castle Point Hall Lot', lat: 40.74648, lng: -74.02400 },
  6: { label: 'Howe Center Lot',       lat: 40.74540, lng: -74.02384 },
};

const HomeScreen: React.FC<Props> = ({ navigation }) => {
  const [showDirections, setShowDirections] = useState(false);

  const pins = [
    { id: 1, top: '82%', left: '30%', name: 'Babbio\nGarage' },
    { id: 2, top: '67%', left: '80%', name: 'River Lot' },
    { id: 3, top: '30%', left: '25%', name: '8th St Lot' },
    { id: 4, top: '16%', left: '70%', name: 'North\nLot' },
    { id: 5, top: '1%',  left: '82%', name: 'Castle Point\nHall Lot' },
    { id: 6, top: '32%', left: '89%', name: 'Howe\nCenter\nLot' },
  ];

  // 2) Open the native maps app at the exact spot
  const openMap = (id: number) => {
    const spot = LOT_COORDINATES[id];
    if (!spot) {
      return Alert.alert('Error', 'Cannot find coordinates for that lot');
    }
    const { lat, lng, label } = spot;
    let url: string;
    if (Platform.OS === 'ios') {
      url = `maps://?q=${encodeURIComponent(label)}&ll=${lat},${lng}`;
    } else {
      url = `geo:${lat},${lng}?q=${lat},${lng}(${encodeURIComponent(label)})`;
    }
    Linking.openURL(url).catch(err =>
      Alert.alert('Error', 'Could not open map: ' + err.message)
    );
  };

  return (
    <View style={styles.screen}>
      {/* 1) Welcome banner */}
      <View style={styles.welcomeBar}>
        <Text style={styles.welcomeText}>Welcome to Stevens!</Text>
      </View>

      {/* 2) Map + pins */}
      <ImageBackground
  source={require('../other/stevensmap.jpg')}
  resizeMode="cover"
  style={styles.background}
>

        <View style={styles.mapContainer}>
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

      {/* 3) Directions button */}
      <TouchableOpacity
        style={styles.directionsButton}
        onPress={() => setShowDirections(true)}
      >
        <Icon name="navigate-circle-outline" size={24} color="#fff" />
        <Text style={styles.directionsButtonText}>Directions</Text>
      </TouchableOpacity>

      {/* 4) Modal list of lots */}
      <Modal
        visible={showDirections}
        animationType="slide"
        transparent
        onRequestClose={() => setShowDirections(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Choose a Lot</Text>
            {pins.map(pin => (
              <TouchableOpacity
                key={pin.id}
                style={styles.modalItem}
                onPress={() => {
                  openMap(pin.id);         // ← use the ID-based lookup
                  setShowDirections(false);
                }}
              >
                <Text style={styles.modalItemText}>
                  {pin.name.replace(/\n/g, ' ')}
                </Text>
              </TouchableOpacity>
            ))}
            <TouchableOpacity
              style={styles.modalCancel}
              onPress={() => setShowDirections(false)}
            >
              <Text style={styles.modalCancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#fff',
  },
  welcomeBar: {
    backgroundColor: '#8B0000',
    paddingVertical: 10,
    alignItems: 'center',
  },
  welcomeText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  background: {
    flex: 1,
    width: '100%',
  },
  mapContainer: {
    flex: 1,
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
    textShadowColor: 'rgba(0,0,0,0.9)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  directionsButton: {
    flexDirection: 'row',
    backgroundColor: '#8B0000',
    paddingVertical: 30,
    paddingHorizontal: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  directionsButtonText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '600',
    marginLeft: 8,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    padding: 20,
    borderTopLeftRadius: 12,
    borderTopRightRadius: 12,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  modalItem: {
    paddingVertical: 12,
  },
  modalItemText: {
    fontSize: 16,
  },
  modalCancel: {
    marginTop: 10,
    alignItems: 'center',
  },
  modalCancelText: {
    fontSize: 16,
    color: '#888',
  },
});

export default HomeScreen;
