import { loadFont } from '@remotion/fonts';
import { staticFile } from 'remotion';

// loadFont gère delayRender/continueRender : le rendu attend les polices.
export const fontsReady = Promise.all([
  loadFont({ family: 'Montserrat', url: staticFile('fonts/Montserrat-Black.ttf'), weight: '900' }),
  loadFont({ family: 'Montserrat', url: staticFile('fonts/Montserrat-ExtraBold.ttf'), weight: '800' }),
]).catch((err: unknown) => {
  console.error('[fonts] échec du chargement de Montserrat', err);
  throw err;
});
