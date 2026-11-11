/**
 * @format
 */

import { AppRegistry, I18nManager } from 'react-native';
import App from './App';
import { name as appName } from './app.json';

// Layout direction follows the language chosen inside the app, not the phone's
// system language, and changes without restarting. The native automatic
// mirroring is therefore switched off (see also android:supportsRtl="false").
I18nManager.allowRTL(false);

AppRegistry.registerComponent(appName, () => App);
