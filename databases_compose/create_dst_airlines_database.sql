CREATE DATABASE IF NOT EXISTS DST_AIRLINES;
USE DST_AIRLINES;

CREATE TABLE IF NOT EXISTS Airports (
  -- id SERIAL PRIMARY KEY,                    -- ID auto-incrémenté comme clé primaire
  airport_code VARCHAR(3) NOT NULL UNIQUE,  -- Code IATA d'aéroport unique // sauf si on nettoie
  latitude FLOAT NOT NULL,       
  longitude FLOAT NOT NULL,       
  name VARCHAR(255) NOT NULL        
);

CREATE TABLE IF NOT EXISTS Flights (
  flight_id SERIAL PRIMARY KEY,                    -- ID de vol auto-incrémenté comme clé primaire
  departure_airport_code VARCHAR(3) NOT NULL,      -- Code IATA de l'aéroport de départ
  departure_scheduled_time_local TIMESTAMP,        -- Heure de départ prévue (locale)
  departure_scheduled_time_utc TIMESTAMP,          -- Heure de départ prévue (UTC)
  departure_actual_time_local TIMESTAMP,           -- Heure de départ réelle (locale)
  departure_actual_time_utc TIMESTAMP,             -- Heure de départ réelle (UTC)
  departure_time_status_code VARCHAR(2),           -- Code du statut du temps de départ (ex: "OT")
  departure_time_status_definition VARCHAR(255),    -- Définition du statut (ex: "Flight On Time")
  departure_terminal_name VARCHAR(255),             -- Nom du terminal de départ
  departure_terminal_gate VARCHAR(255),             -- Porte du terminal de départ
  arrival_airport_code VARCHAR(3) NOT NULL,        -- Code IATA de l'aéroport d'arrivée
  arrival_scheduled_time_local TIMESTAMP,          -- Heure d'arrivée prévue (locale)
  arrival_scheduled_time_utc TIMESTAMP,            -- Heure d'arrivée prévue (UTC)
  arrival_actual_time_local TIMESTAMP,             -- Heure d'arrivée réelle (locale)
  arrival_actual_time_utc TIMESTAMP,               -- Heure d'arrivée réelle (UTC)
  arrival_time_status_code VARCHAR(2),             -- Code du statut du temps d'arrivée (ex: "OT")
  arrival_time_status_definition VARCHAR(255),      -- Définition du statut (ex: "Flight On Time")
  arrival_terminal_name VARCHAR(255),               -- Nom du terminal d'arrivée
  marketing_carrier_airline_id VARCHAR(10),        -- ID de la compagnie aérienne commerciale
  marketing_carrier_flight_number VARCHAR(10),     -- Numéro de vol de la compagnie commerciale
  operating_carrier_airline_id VARCHAR(10),        -- ID de la compagnie aérienne opérante
  operating_carrier_flight_number VARCHAR(10),     -- Numéro de vol de la compagnie opérante
  equipment_aircraft_code VARCHAR(10),             -- Code de l'avion
  equipment_aircraft_registration VARCHAR(10),     -- Immatriculation de l'avion
  flight_status_code VARCHAR(2),                   -- Code de statut du vol (ex: "LD" pour landed)
  flight_status_definition VARCHAR(255),            -- Définition du statut du vol
  service_type VARCHAR(255),                        -- Type de service (ex: "Passenger")
  arrival_estimated_time_local TIMESTAMP,          -- Heure estimée d'arrivée (locale)
  arrival_estimated_time_utc TIMESTAMP,            -- Heure estimée d'arrivée (UTC)
  arrival_terminal_gate VARCHAR(10),               -- Porte du terminal d'arrivée
  departure_estimated_time_local TIMESTAMP,        -- Heure estimée de départ (locale)
  departure_estimated_time_utc TIMESTAMP           -- Heure estimée de départ (UTC)
);

CREATE TABLE IF NOT EXISTS Weather (
    Flight_DateTime DATETIME NULL,                     -- Date et heure du vol
    Airport_Code VARCHAR(10) NULL,                     -- Code de l'aéroport (IATA/ICAO)
    Latitude FLOAT NULL,                               -- Latitude de l'aéroport
    Longitude FLOAT NULL,                              -- Longitude de l'aéroport
    temperature_2m FLOAT NULL,                         -- Température à 2 mètres au-dessus du sol
    relative_humidity_2m FLOAT NULL,                   -- Humidité relative à 2 mètres
    dew_point_2m FLOAT NULL,                           -- Température du point de rosée à 2 mètres
    apparent_temperature FLOAT NULL,                   -- Température ressentie
    precipitation_probability FLOAT NULL,              -- Probabilité de précipitations
    precipitation FLOAT NULL,                          -- Quantité totale de précipitations
    rain FLOAT NULL,                                   -- Précipitations sous forme de pluie
    showers FLOAT NULL,                                -- Averses
    snowfall FLOAT NULL,                               -- Chute de neige
    snow_depth FLOAT NULL,                             -- Profondeur de la neige
    weather_code FLOAT NULL,                           -- Code météo
    pressure_msl FLOAT NULL,                           -- Pression au niveau de la mer
    surface_pressure FLOAT NULL,                       -- Pression à la surface
    cloud_cover FLOAT NULL,                            -- Couverture nuageuse totale
    cloud_cover_low FLOAT NULL,                        -- Couverture nuageuse basse
    cloud_cover_mid FLOAT NULL,                        -- Couverture nuageuse moyenne
    cloud_cover_high FLOAT NULL,                       -- Couverture nuageuse haute
    visibility FLOAT NULL,                             -- Visibilité (en km)
    evapotranspiration FLOAT NULL,                     -- Évapotranspiration totale
    et0_fao_evapotranspiration FLOAT NULL,             -- Évapotranspiration FAO ET0
    vapour_pressure_deficit FLOAT NULL,                -- Déficit de pression de vapeur
    wind_speed_10m FLOAT NULL,                         -- Vitesse du vent à 10 mètres
    wind_speed_80m FLOAT NULL,                         -- Vitesse du vent à 80 mètres
    wind_speed_120m FLOAT NULL,                        -- Vitesse du vent à 120 mètres
    wind_speed_180m FLOAT NULL,                        -- Vitesse du vent à 180 mètres
    wind_direction_10m FLOAT NULL,                     -- Direction du vent à 10 mètres
    wind_direction_80m FLOAT NULL,                     -- Direction du vent à 80 mètres
    wind_direction_120m FLOAT NULL,                    -- Direction du vent à 120 mètres
    wind_direction_180m FLOAT NULL,                    -- Direction du vent à 180 mètres
    wind_gusts_10m FLOAT NULL,                         -- Rafales de vent à 10 mètres
    temperature_80m FLOAT NULL,                        -- Température à 80 mètres
    temperature_120m FLOAT NULL,                       -- Température à 120 mètres
    temperature_180m FLOAT NULL,                       -- Température à 180 mètres
    soil_temperature_0cm FLOAT NULL,                   -- Température du sol à 0 cm
    soil_temperature_6cm FLOAT NULL,                   -- Température du sol à 6 cm
    soil_temperature_18cm FLOAT NULL,                  -- Température du sol à 18 cm
    soil_temperature_54cm FLOAT NULL,                  -- Température du sol à 54 cm
    soil_moisture_0_to_1cm FLOAT NULL,                 -- Humidité du sol entre 0 et 1 cm
    soil_moisture_1_to_3cm FLOAT NULL,                 -- Humidité du sol entre 1 et 3 cm
    soil_moisture_3_to_9cm FLOAT NULL,                 -- Humidité du sol entre 3 et 9 cm
    soil_moisture_9_to_27cm FLOAT NULL,                -- Humidité du sol entre 9 et 27 cm
    soil_moisture_27_to_81cm FLOAT NULL                -- Humidité du sol entre 27 et 81 cm

  CONSTRAINT fk_arrival_airport FOREIGN KEY (Airport_Code) REFERENCES Airports(airport_code) -- Clé étrangère liée à la table Airports
);

-- CREATE TABLE IF NOT EXISTS Weather (
--   weather_id SERIAL PRIMARY KEY,                  -- ID météo auto-incrémenté comme clé primaire
--   date DATE NOT NULL,                             -- Date de la météo
--   weather_code FLOAT NOT NULL,                    -- Code météo
--   temperature_2m_max FLOAT NOT NULL,              -- Température maximale à 2m
--   temperature_2m_min FLOAT NOT NULL,              -- Température minimale à 2m
--   precipitation_sum FLOAT NOT NULL,               -- Somme des précipitations
--   rain_sum FLOAT NOT NULL,                        -- Somme des pluies
--   snowfall_sum FLOAT NOT NULL,                    -- Somme des chutes de neige
--   precipitation_probability_max FLOAT NOT NULL,   -- Probabilité maximale de précipitations
--   wind_speed_10m_max FLOAT NOT NULL,              -- Vitesse maximale du vent à 10m
--   wind_gusts_10m_max FLOAT NOT NULL,              -- Rafales de vent maximales à 10m
--   wind_direction_10m_dominant FLOAT NOT NULL,     -- Direction dominante du vent à 10m
--   apparent_temperature_max FLOAT NOT NULL,        -- Température ressentie maximale
--   apparent_temperature_min FLOAT NOT NULL,        -- Température ressentie minimale
--   sunrise TIME NOT NULL,                          -- Heure du lever du soleil
--   sunset TIME NOT NULL,                           -- Heure du coucher du soleil
--   daylight_duration FLOAT NOT NULL,               -- Durée d'ensoleillement
--   sunshine_duration FLOAT NOT NULL,               -- Durée totale d'ensoleillement
--   uv_index_max FLOAT NOT NULL,                    -- Indice UV maximal
--   uv_index_clear_sky_max FLOAT NOT NULL,          -- Indice UV maximal par ciel dégagé
--   precipitation_hours FLOAT NOT NULL,             -- Heures de précipitations
--   showers_sum FLOAT NOT NULL,                     -- Somme des averses
--   shortwave_radiation_sum FLOAT NOT NULL,         -- Somme de la radiation à ondes courtes
--   et0_fao_evapotranspiration FLOAT NOT NULL,      -- Evapotranspiration ET0 FAO
--   airport_code VARCHAR(3) NOT NULL,               -- Code IATA de l'aéroport (référence à Airports)
  
--   CONSTRAINT fk_arrival_airport FOREIGN KEY (airport_code) REFERENCES Airports(airport_code) -- Clé étrangère liée à la table Airports
-- );

CREATE TABLE IF NOT EXISTS Airlines (
  airline_id VARCHAR(3) PRIMARY KEY,               -- ID de la compagnie aérienne (AirlineID)
  airline_id_icao VARCHAR(3) NOT NULL,             -- Code ICAO de la compagnie aérienne (AirlineID_ICAO)
  name VARCHAR(255) NOT NULL                      -- Nom de la compagnie aérienne (ex: "Amber Air")
);

CREATE TABLE IF NOT EXISTS Aircrafts (
    AircraftCode INT PRIMARY KEY,          -- Code unique pour chaque type d'avion
    Names VARCHAR(255) NOT NULL,                   -- Détails du nom, stockés en format JSON
    AirlineEquipCode VARCHAR(10) NOT NULL  -- Code d'équipement de la compagnie aérienne
);

