import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './screens/HomeScreen';
import GoogleSheetsScreen from './screens/ParkingScreen';

export type RootStackParamList = {
  ROOST: undefined;
  AvailableParkingSpaces: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App(): React.JSX.Element {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="ROOST">
        <Stack.Screen 
          name="ROOST" 
          component={HomeScreen} 
          options={{
            title: 'STEVENS ROOST',  
            headerTitleAlign: 'center', 
            headerStyle: {
              backgroundColor: '#8B0000', 
            },
            headerTintColor: '#fff',  
            headerTitleStyle: {
              fontWeight: 'bold', 
              fontSize: 24,
              fontFamily: 'IBMPlexSans-Regular',
            },
          }}
        />
        <Stack.Screen 
          name="AvailableParkingSpaces" 
          component={GoogleSheetsScreen}
          options={{
            title: 'Available Parking',
            headerTitleAlign: 'center',
            headerStyle: {
              backgroundColor: '#8B0000',
            },
            headerTintColor: '#fff',
            headerTitleStyle: {
              fontSize: 24,
              fontFamily: 'IBMPlexSans-Regular', 
            },
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
