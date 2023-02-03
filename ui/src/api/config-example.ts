/*
Complete this configuration and save in this directory as `config.ts`
*/

interface APIConfig {
  delineateURL: string;
  mapboxToken: string;
  mapStyle: string;
}

export default {
  delineateURL: '', // URL for the delineation API
  mapboxToken: '', // Mapbox GL token
  mapStyle: '', // Mapbox basemap style url. Ex. 'mapbox://styles/mapbox/streets-v11'
} as APIConfig;
