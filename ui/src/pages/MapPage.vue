<template>
  <q-page style="overflow: hidden">
    <div class="container">
      <div id="map" class="map"></div>
    </div>

    <div v-show="delineating" class="absolute-center">
      <q-spinner-bars color="white" size="70" />
    </div>

    <Transition name="fade">
      <div class="finished" v-show="finished">
        <q-img :src="finishedImage" fit="contain" class="finished-img"></q-img>
      </div>
    </Transition>

    <Transition name="slide-fade">
      <div class="infographic" v-if="infographic">
        <div class="notification">
          <q-card
            elevation-19
            :color="notification.type === 'info' ? 'white' : 'error'"
          >
            <q-card-section class="info-card">
              <div class="row align-center justify-center">
                <div v-html="notification.message"></div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <q-img
          :src="require('../assets/ryan.png')"
          fit="contain"
          class="infographic-img"
        ></q-img>
      </div>
    </Transition>
  </q-page>
</template>

<script setup lang="ts">
import mapboxgl, { GeoJSONSource, Map, MapMouseEvent } from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { ref, reactive, computed, onMounted } from 'vue';
import axios from 'axios';
import apiConfig from '../api/config';
import { Feature } from 'geojson';

const showNotification = (type: string, message: string) => {
  notification.type = type;
  notification.message = message;
  infographic.value = true;
  setTimeout(() => {
    infographic.value = false;
  }, 3000);
};

const notification = reactive({
  type: '',
  message: '',
});

const images = [
  require('../assets/fin_1.png'),
  require('../assets/fin_2.png'),
  require('../assets/fin_3.png'),
  require('../assets/fin_4.png'),
  require('../assets/fin_5.png'),
  require('../assets/fin_6.png'),
  require('../assets/fin_7.png'),
  require('../assets/fin_8.png'),
];

const finishedImageNumber = ref(0);
const finishedImage = computed(() => images[finishedImageNumber.value]);
const finished = ref(false);

const changeFinishedImage = () => {
  finishedImageNumber.value = Math.floor(Math.random() * 9);
};

const infographic = ref(false);

let map: Map;

interface GeoJson {
  type: string;
  coordinates: Array<Array<Array<Array<number>>>>;
}

const zoomToLayer = (geo: GeoJson) => {
  const polygons = geo.coordinates;
  const first_polygon = polygons[0];

  const bounds = new mapboxgl.LngLatBounds(
    { lng: first_polygon[0][0][0], lat: first_polygon[0][0][1] },
    { lng: first_polygon[0][0][0], lat: first_polygon[0][0][1] }
  );

  for (let polygon of polygons) {
    for (let coord of polygon[0]) {
      bounds.extend([coord[0], coord[1]]);
    }
  }

  map.fitBounds(bounds, {
    padding: 80,
  });
};

const delineating = ref(false);

const initMap = async () => {
  mapboxgl.accessToken = apiConfig.mapboxToken;

  map = new Map({
    container: 'map',
    style: apiConfig.mapStyle,
    zoom: 4.3,
    center: [-106, 54],
    projection: {
      name: 'globe',
    },
  });

  map.on('load', () => {
    map.getCanvas().style.cursor = 'pointer';

    map.setFog({});

    map.addSource('hillshade-dem', {
      type: 'raster-dem',
      url: 'mapbox://mapbox.mapbox-terrain-dem-v1',
    });
    map.addLayer({
      id: 'hillshading',
      source: 'hillshade-dem',
      type: 'hillshade',
    });

    map.addSource('watershed', {
      type: 'geojson',
      data: {
        type: 'MultiPolygon',
        coordinates: [[[]]],
      },
    });

    map.addLayer({
      id: 'watershed-layer',
      type: 'fill',
      source: 'watershed',
      paint: {
        'fill-color': '#0080ff',
        'fill-opacity': 0.5,
      },
    });

    map.flyTo({
      zoom: 6.5,
      center: [-120.9, 56.9],
      curve: 4,
      duration: 4000,
      essential: true,
    });
  });

  interface DelineateResult {
    response: string;
    x?: number;
    y?: number;
    area?: number;
    res?: number;
    geo?: Feature;
    error?: string;
  }

  map.on('click', (e: MapMouseEvent) => {
    if (delineating.value) return;
    delineating.value = true;

    axios
      .post(apiConfig.delineateURL, {
        x: e.lngLat.lng,
        y: e.lngLat.lat,
        crs: 4326,
      })
      .then((response) => {
        const result: DelineateResult = response.data;
        if (result.response === 'success') {
          if (result.geo) {
            changeFinishedImage();
            finished.value = true;

            (map.getSource('watershed') as GeoJSONSource).setData(result.geo);
            zoomToLayer(result.geo);

            setTimeout(() => {
              finished.value = false;
            }, 1000);

            setTimeout(() => {
              showNotification(
                'info',
                `This one was derived using ${result.res}m cells and is ${
                  result.area ? Math.round(result.area / 1e4) / 1e2 : '?'
                } km<sup>2</sup> !`
              );
            }, 1000);
          }
        } else {
          const message: string = result.error
            ? result.error.split('\n').slice(-2)[0]
            : '';

          showNotification('error', message);
        }
      })
      .catch((error) => {
        showNotification('error', error);
      })
      .finally(() => {
        delineating.value = false;
      });
  });
};

onMounted(() => {
  initMap();
  setTimeout(() => {
    showNotification('info', 'Click on a stream!');
  }, 3000);
});
</script>

<style scoped lang="scss">
.container {
  position: relative;
  height: 100vh;
}
.map {
  position: relative;
  top: 0;
  left: 0;
  height: 100%;
  width: 100%;
}
.mapboxgl-canvas-container {
  cursor: pointer, auto !important;
}
.controls {
  position: absolute;
  top: 20px;
  left: 20px;
  bottom: 20px;
  width: 25%;
}
.progress {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-content: center;
}
.finished {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
}
.finished-img {
  max-width: 400px;
}
.infographic {
  position: relative;
}
.notification {
  position: absolute;
  margin-bottom: 150px;
  bottom: 0;
  left: 400px;
  right: 0;
  margin-left: auto;
  margin-right: auto;
  height: 100px;
  width: 300px;
}
.infographic-img {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  margin-left: auto;
  margin-right: auto;
  max-width: 150px;
}
.info-card {
  text-align: center;
  font-family: 'Comic Neue', cursive;
  font-weight: bold;
}
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.8s cubic-bezier(1, 0.5, 0.8, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(200px);
  opacity: 0;
}
</style>
