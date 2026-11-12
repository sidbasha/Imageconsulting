/* eslint-env jest */
import mockSafeAreaContext from 'react-native-safe-area-context/jest/mock';

jest.mock('react-native-safe-area-context', () => mockSafeAreaContext);
jest.mock('react-native-keychain');
jest.mock('react-native-image-picker', () => ({ launchImageLibrary: jest.fn(), launchCamera: jest.fn() }));
jest.mock('@react-native-community/geolocation');
// Icons and SVG are native drawing; in tests they render nothing.
jest.mock('lucide-react-native', () => new Proxy({}, { get: (_, name) => (name === '__esModule' ? true : () => null) }));
jest.mock('react-native-svg', () => new Proxy({}, { get: (_, name) => (name === '__esModule' ? true : () => null) }));
