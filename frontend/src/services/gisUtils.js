/**
 * GIS utility functions for coordinate transformations,
 * distance calculations, and geometric operations.
 */

/**
 * Fetch application configuration from the API.
 * Cached for the session.
 */
let cachedConfig = null;
export const fetchAppConfig = async (apiClient) => {
  if (cachedConfig) return cachedConfig;
  try {
    const response = await apiClient.get('/api/v1/config');
    cachedConfig = response.data;
    return cachedConfig;
  } catch (err) {
    console.error('Failed to fetch app config:', err);
    return null;
  }
};

/**
 * Calculate distance between two points using Haversine formula
 * @param {number} lat1 - Latitude of point 1
 * @param {number} lon1 - Longitude of point 1
 * @param {number} lat2 - Latitude of point 2
 * @param {number} lon2 - Longitude of point 2
 * @returns {number} Distance in meters
 */
export const calculateDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371e3; // Earth's radius in meters
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δφ = ((lat2 - lat1) * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
};

/**
 * Calculate total distance for a path of points
 * @param {Array} points - Array of {latitude, longitude} objects
 * @returns {number} Total distance in meters
 */
export const calculatePathDistance = (points) => {
  if (!points || points.length < 2) return 0;

  let totalDistance = 0;
  for (let i = 0; i < points.length - 1; i++) {
    const p1 = points[i];
    const p2 = points[i + 1];
    totalDistance += calculateDistance(p1.latitude, p1.longitude, p2.latitude, p2.longitude);
  }

  return totalDistance;
};

/**
 * Calculate bearing between two points
 * @param {number} lat1 - Latitude of point 1
 * @param {number} lon1 - Longitude of point 1
 * @param {number} lat2 - Latitude of point 2
 * @param {number} lon2 - Longitude of point 2
 * @returns {number} Bearing in degrees (0-360)
 */
export const calculateBearing = (lat1, lon1, lat2, lon2) => {
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;

  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  const θ = Math.atan2(y, x);

  return ((θ * 180) / Math.PI + 360) % 360;
};

/**
 * Calculate midpoint between two points
 * @param {number} lat1 - Latitude of point 1
 * @param {number} lon1 - Longitude of point 1
 * @param {number} lat2 - Latitude of point 2
 * @param {number} lon2 - Longitude of point 2
 * @returns {Object} {latitude, longitude} of midpoint
 */
export const calculateMidpoint = (lat1, lon1, lat2, lon2) => {
  const φ1 = (lat1 * Math.PI) / 180;
  const λ1 = (lon1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const λ2 = (lon2 * Math.PI) / 180;

  const Bx = Math.cos(φ2) * Math.cos(λ2 - λ1);
  const By = Math.cos(φ2) * Math.sin(λ2 - λ1);

  const φ3 = Math.atan2(
    Math.sin(φ1) + Math.sin(φ2),
    Math.sqrt((Math.cos(φ1) + Bx) * (Math.cos(φ1) + Bx) + By * By)
  );
  const λ3 = λ1 + Math.atan2(By, Math.cos(φ1) + Bx);

  return {
    latitude: (φ3 * 180) / Math.PI,
    longitude: ((λ3 * 180) / Math.PI + 540) % 360 - 180,
  };
};

/**
 * Calculate bounds from an array of points
 * @param {Array} points - Array of {latitude, longitude} objects
 * @returns {Object} Bounds object {north, south, east, west}
 */
export const calculateBounds = (points) => {
  if (!points || points.length === 0) {
    return {
      north: 0,
      south: 0,
      east: 0,
      west: 0,
    };
  }

  const latitudes = points.map((p) => p.latitude);
  const longitudes = points.map((p) => p.longitude);

  return {
    north: Math.max(...latitudes),
    south: Math.min(...latitudes),
    east: Math.max(...longitudes),
    west: Math.min(...longitudes),
  };
};

/**
 * Calculate center point from bounds
 * @param {Object} bounds - Bounds object {north, south, east, west}
 * @returns {Object} Center point {latitude, longitude}
 */
export const calculateCenter = (bounds) => {
  return {
    latitude: (bounds.north + bounds.south) / 2,
    longitude: (bounds.east + bounds.west) / 2,
  };
};

/**
 * Simplify polyline using Douglas-Peucker algorithm
 * @param {Array} points - Array of {latitude, longitude} objects
 * @param {number} tolerance - Tolerance in meters
 * @returns {Array} Simplified points array
 */
export const simplifyPolyline = (points, tolerance) => {
  if (points.length <= 2) return points;

  // Find the point with the maximum distance
  let maxDistance = 0;
  let maxIndex = 0;
  const firstPoint = points[0];
  const lastPoint = points[points.length - 1];

  for (let i = 1; i < points.length - 1; i++) {
    const distance = perpendicularDistance(points[i], firstPoint, lastPoint);
    if (distance > maxDistance) {
      maxDistance = distance;
      maxIndex = i;
    }
  }

  // If max distance is greater than tolerance, recursively simplify
  if (maxDistance > tolerance) {
    const left = simplifyPolyline(points.slice(0, maxIndex + 1), tolerance);
    const right = simplifyPolyline(points.slice(maxIndex), tolerance);

    // Combine results, removing duplicate point
    return left.slice(0, left.length - 1).concat(right);
  } else {
    // All points within tolerance, return endpoints
    return [firstPoint, lastPoint];
  }
};

/**
 * Calculate perpendicular distance from point to line
 * @private
 */
const perpendicularDistance = (point, lineStart, lineEnd) => {
  const area = Math.abs(
    0.5 *
      (lineStart.longitude * lineEnd.latitude +
        lineEnd.longitude * point.latitude +
        point.longitude * lineStart.latitude -
        lineEnd.longitude * lineStart.latitude -
        point.longitude * lineEnd.latitude -
        lineStart.longitude * point.latitude)
  );

  const lineLength = calculateDistance(
    lineStart.latitude,
    lineStart.longitude,
    lineEnd.latitude,
    lineEnd.longitude
  );

  return lineLength > 0 ? (2 * area) / lineLength : 0;
};

/**
 * Convert degrees to radians
 * @param {number} degrees - Angle in degrees
 * @returns {number} Angle in radians
 */
export const degreesToRadians = (degrees) => {
  return degrees * (Math.PI / 180);
};

/**
 * Convert radians to degrees
 * @param {number} radians - Angle in radians
 * @returns {number} Angle in degrees
 */
export const radiansToDegrees = (radians) => {
  return radians * (180 / Math.PI);
};

/**
 * Format distance with appropriate units
 * @param {number} meters - Distance in meters
 * @returns {string} Formatted distance string
 */
export const formatDistance = (meters) => {
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  } else if (meters < 10000) {
    return `${(meters / 1000).toFixed(2)} km`;
  } else {
    return `${Math.round(meters / 1000)} km`;
  }
};

/**
 * Format area with appropriate units
 * @param {number} squareMeters - Area in square meters
 * @returns {string} Formatted area string
 */
export const formatArea = (squareMeters) => {
  if (squareMeters < 10000) {
    return `${Math.round(squareMeters)} m²`;
  } else if (squareMeters < 1000000) {
    return `${(squareMeters / 10000).toFixed(2)} ha`;
  } else {
    return `${(squareMeters / 1000000).toFixed(2)} km²`;
  }
};

/**
 * Calculate elevation statistics
 * @param {Array} elevations - Array of elevation values
 * @returns {Object} Elevation statistics
 */
export const calculateElevationStats = (elevations) => {
  if (!elevations || elevations.length === 0) {
    return {
      min: 0,
      max: 0,
      avg: 0,
      totalAscent: 0,
      totalDescent: 0,
    };
  }

  let totalAscent = 0;
  let totalDescent = 0;

  for (let i = 1; i < elevations.length; i++) {
    const diff = elevations[i] - elevations[i - 1];
    if (diff > 0) {
      totalAscent += diff;
    } else {
      totalDescent += Math.abs(diff);
    }
  }

  return {
    min: Math.min(...elevations),
    max: Math.max(...elevations),
    avg: elevations.reduce((a, b) => a + b, 0) / elevations.length,
    totalAscent,
    totalDescent,
  };
};

/**
 * Calculate slope between two points
 * @param {number} elevation1 - Elevation at point 1
 * @param {number} elevation2 - Elevation at point 2
 * @param {number} distance - Horizontal distance between points
 * @returns {number} Slope in percent
 */
export const calculateSlope = (elevation1, elevation2, distance) => {
  if (distance === 0) return 0;
  const elevationDiff = elevation2 - elevation1;
  return (elevationDiff / distance) * 100;
};

/**
 * Convert coordinate format (DD to DMS)
 * @param {number} decimalDegrees - Coordinate in decimal degrees
 * @param {boolean} isLatitude - Whether this is a latitude coordinate
 * @returns {string} Coordinate in DMS format
 */
export const decimalToDMS = (decimalDegrees, isLatitude) => {
  const direction = isLatitude
    ? decimalDegrees >= 0
      ? 'N'
      : 'S'
    : decimalDegrees >= 0
    ? 'E'
    : 'W';

  const absolute = Math.abs(decimalDegrees);
  const degrees = Math.floor(absolute);
  const minutesNotTruncated = (absolute - degrees) * 60;
  const minutes = Math.floor(minutesNotTruncated);
  const seconds = ((minutesNotTruncated - minutes) * 60).toFixed(2);

  return `${degrees}° ${minutes}' ${seconds}" ${direction}`;
};

/**
 * Parse DMS coordinate to decimal degrees
 * @param {string} dmsString - Coordinate in DMS format
 * @returns {number} Coordinate in decimal degrees
 */
export const parseDMSToDecimal = (dmsString) => {
  const parts = dmsString.split(/[^\d\w\.]+/);
  const degrees = parseFloat(parts[0]);
  const minutes = parseFloat(parts[1]);
  const seconds = parseFloat(parts[2]);
  const direction = parts[3];

  let decimal = degrees + minutes / 60 + seconds / 3600;

  if (direction === 'S' || direction === 'W') {
    decimal = -decimal;
  }

  return decimal;
};

/**
 * Generate GeoJSON from points
 * @param {Array} points - Array of {latitude, longitude, elevation} objects
 * @param {string} type - Geometry type ('Point', 'LineString', 'Polygon')
 * @returns {Object} GeoJSON feature
 */
export const pointsToGeoJSON = (points, type = 'LineString') => {
  const coordinates = points.map((p) => [
    p.longitude,
    p.latitude,
    p.elevation || 0,
  ]);

  let geometry;
  switch (type) {
    case 'Point':
      geometry = {
        type: 'Point',
        coordinates: coordinates[0],
      };
      break;
    case 'Polygon':
      geometry = {
        type: 'Polygon',
        coordinates: [coordinates],
      };
      break;
    case 'LineString':
    default:
      geometry = {
        type: 'LineString',
        coordinates: coordinates,
      };
      break;
  }

  return {
    type: 'Feature',
    geometry: geometry,
    properties: {
      pointsCount: points.length,
      totalDistance: calculatePathDistance(points),
    },
  };
};

/**
 * Calculate intersection of two lines
 * @param {Array} line1 - Array of two points [{lat, lon}, {lat, lon}]
 * @param {Array} line2 - Array of two points [{lat, lon}, {lat, lon}]
 * @returns {Object|null} Intersection point or null if no intersection
 */
export const calculateLineIntersection = (line1, line2) => {
  const [p1, p2] = line1;
  const [p3, p4] = line2;

  const denominator =
    (p1.latitude - p2.latitude) * (p3.longitude - p4.longitude) -
    (p1.longitude - p2.longitude) * (p3.latitude - p4.latitude);

  if (denominator === 0) {
    return null; // Lines are parallel
  }

  const t =
    ((p1.latitude - p3.latitude) * (p3.longitude - p4.longitude) -
      (p1.longitude - p3.longitude) * (p3.latitude - p4.latitude)) /
    denominator;
  const u =
    -(
      (p1.latitude - p2.latitude) * (p1.longitude - p3.longitude) -
      (p1.longitude - p2.longitude) * (p1.latitude - p3.latitude)
    ) / denominator;

  if (t >= 0 && t <= 1 && u >= 0 && u <= 1) {
    return {
      latitude: p1.latitude + t * (p2.latitude - p1.latitude),
      longitude: p1.longitude + t * (p2.longitude - p1.longitude),
    };
  }

  return null; // Intersection is outside line segments
};

/**
 * Buffer a point by a given distance
 * @param {number} lat - Latitude
 * @param {number} lon - Longitude
 * @param {number} distance - Distance in meters
 * @param {number} points - Number of points in buffer polygon
 * @returns {Array} Array of points forming the buffer polygon
 */
export const bufferPoint = (lat, lon, distance, points = 32) => {
  const R = 6371e3; // Earth's radius in meters
  const angularDistance = distance / R;
  const bufferPoints = [];

  for (let i = 0; i < points; i++) {
    const bearing = (i * 360) / points;
    const φ1 = (lat * Math.PI) / 180;
    const λ1 = (lon * Math.PI) / 180;
    const θ = (bearing * Math.PI) / 180;

    const φ2 = Math.asin(
      Math.sin(φ1) * Math.cos(angularDistance) +
        Math.cos(φ1) * Math.sin(angularDistance) * Math.cos(θ)
    );

    const λ2 =
      λ1 +
      Math.atan2(
        Math.sin(θ) * Math.sin(angularDistance) * Math.cos(φ1),
        Math.cos(angularDistance) - Math.sin(φ1) * Math.sin(φ2)
      );

    bufferPoints.push({
      latitude: (φ2 * 180) / Math.PI,
      longitude: ((λ2 * 180) / Math.PI + 540) % 360 - 180,
    });
  }

  // Close the polygon
  bufferPoints.push(bufferPoints[0]);

  return bufferPoints;
};