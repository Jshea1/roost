import React, { useState, useEffect } from 'react';
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
import { fetchGoogleSheetsData } from '../services/googleSheets';

type Props = NativeStackScreenProps<RootStackParamList, 'ROOST'>;

const LOT_COORDINATES: Record<
  number,
  { label: string; lat: number; lng: number }
> = {
  1: { label: 'Babbio Garage', lat: 40.74257, lng: -74.02608 },
  2: { label: 'River Lot', lat: 40.74333, lng: -74.02477 },
  3: { label: '8th St Lot', lat: 40.74552, lng: -74.02620 },
  4: { label: 'North Lot', lat: 40.74645, lng: -74.02481 },
  5: { label: 'Castle Point Hall Lot', lat: 40.74648, lng: -74.02400 },
  6: { label: 'Howe Center Lot', lat: 40.74540, lng: -74.02384 },
};

export default function HomeScreen({ navigation }: Props) {
  const [showDirections, setShowDirections] = useState(false);
  const [totalOpen, setTotalOpen] = useState<number>(0);

  useEffect(() => {
    let isMounted = true;
    const fetchCount = async () => {
      try {
        const sheetData = await fetchGoogleSheetsData();
        const raw = sheetData?.[1]?.[2];
        const num = parseInt(raw ?? '', 10);
        if (isMounted) setTotalOpen(isNaN(num) ? 0 : num);
      } catch (e) {
        console.error('Error loading open-spot count:', e);
      }
    };
    fetchCount();
    const handle = setInterval(fetchCount, 3000);
    return () => {
      isMounted = false;
      clearInterval(handle);
    };
  }, []);

  const pins = [
    { id: 1, top: '78%', left: '39%', name: 'Babbio\nGarage' },
    { id: 2, top: '64%', left: '77%', name: 'River Lot' },
    { id: 3, top: '32%', left: '30%', name: '8th St Lot' },
    { id: 4, top: '16%', left: '67%', name: 'North\nLot' },
    { id: 5, top: '3%',  left: '75%', name: 'Castle Point\nHall Lot' },
    { id: 6, top: '33%', left: '84%', name: 'Howe\nCenter\nLot' },
  ];

  const openMap = (id: number) => {
    const spot = LOT_COORDINATES[id];
    if (!spot) return Alert.alert('Error', 'Cannot find coordinates for that lot');
    const { lat, lng, label } = spot;
    const url =
      Platform.OS === 'ios'
        ? `maps://?q=${encodeURIComponent(label)}&ll=${lat},${lng}`
        : `geo:${lat},${lng}?q=${lat},${lng}(${encodeURIComponent(label)})`;
    Linking.openURL(url).catch(err =>
      Alert.alert('Error', 'Could not open map: ' + err.message)
    );
  };

  return (
    <View style={styles.screen}>
      <View style={styles.welcomeBar}>
        <Text style={styles.welcomeText}>Welcome to Stevens!</Text>
      </View>

      <ImageBackground
        source={require('../other/stevensmap.jpg')}
        resizeMode="cover"
        style={styles.background}
      >
        <View style={styles.mapContainer}>
          {pins.map(pin => {
            const isBabbio = pin.id === 1;
            const Container: any = isBabbio ? TouchableOpacity : View;

            return (
              <Container
                key={pin.id}
                style={[styles.marker, { top: pin.top as any, left: pin.left as any }]}
                {...(isBabbio
                  ? { onPress: () => navigation.navigate('AvailableParkingSpaces') }
                  : {})}
              >
                {/* icon + (only for Babbio) badge */}
                <View style={styles.pinIconContainer}>
                  <Icon name="location-sharp" size={30} color="red" />
                  {isBabbio && (
                    <View style={styles.badge}>
                      <Text style={styles.badgeText}>{totalOpen}</Text>
                    </View>
                  )}
                </View>

                {/* every spot shows its name */}
                <View style={styles.pinBubble}>
                  <Text style={styles.pinBubbleText}>{pin.name}</Text>
                </View>
              </Container>
            );
          })}
        </View>
      </ImageBackground>

      <TouchableOpacity
        style={styles.directionsButton}
        onPress={() => setShowDirections(true)}
      >
        <Icon name="navigate-circle-outline" size={24} color="#fff" />
        <Text style={styles.directionsButtonText}>Directions</Text>
      </TouchableOpacity>

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
                  openMap(pin.id);
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
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#fff' },
  welcomeBar: {
    backgroundColor: '#8B0000',
    paddingVertical: 10,
    alignItems: 'center',
  },
  welcomeText: { color: '#fff', fontSize: 18, fontWeight: '600' },
  background: { flex: 1, width: '100%' },
  mapContainer: { flex: 1 },

  marker: {
    position: 'absolute',
    alignItems: 'center',
  },
  pinIconContainer: {
    position: 'relative',
    width: 30,
    height: 30,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    position: 'absolute',
    top: -15,
    backgroundColor: '#fff',
    borderColor: '#8B0000',
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 4,
    paddingVertical: 2,
  },
  badgeText: {
    color: '#8B0000',
    fontSize: 10,
    fontWeight: 'bold',
    textAlign: 'center',
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
  modalTitle: { fontSize: 18, fontWeight: '600', marginBottom: 12 },
  modalItem: { paddingVertical: 12 },
  modalItemText: { fontSize: 16 },
  modalCancel: { marginTop: 10, alignItems: 'center' },
  modalCancelText: { fontSize: 16, color: '#888' },
});
