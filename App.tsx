import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './screens/HomeScreen';
import GoogleSheetsScreen from './screens/ParkingScreen';

export type RootStackParamList = {
  Home: undefined;
  GoogleSheets: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App(): React.JSX.Element {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="GoogleSheets" component={GoogleSheetsScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
