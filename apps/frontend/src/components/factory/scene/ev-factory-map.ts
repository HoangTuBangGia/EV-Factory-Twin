import * as THREE from 'three';
import {
  AMR_FLEET_DATA,
  FACTORY_ZONES,
} from "./ev-factory-data";

// Helper canvas textures for industrial surfaces
export function createHazardTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(0, 0, 256, 256);
    ctx.fillStyle = '#111827';
    ctx.beginPath();
    for (let i = -256; i < 512; i += 64) {
      ctx.moveTo(i, 0);
      ctx.lineTo(i + 32, 0);
      ctx.lineTo(i + 256 + 32, 256);
      ctx.lineTo(i + 256, 256);
    }
    ctx.fill();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  return texture;
}

export function createFloorGridTexture(color: string, lineColor: string, size = 512): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, size, size);
    
    // Grid lines (1m intervals)
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.rect(0, 0, size, size);
    ctx.stroke();

    // Subtle texture noise
    ctx.fillStyle = 'rgba(255,255,255,0.02)';
    for (let i = 0; i < 400; i++) {
      const rx = Math.random() * size;
      const ry = Math.random() * size;
      ctx.fillRect(rx, ry, 2, 2);
    }
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  return texture;
}

export function createSignTexture(text: string, subText: string, bgColor = '#1e293b', textColor = '#38bdf8', width = 512, height = 128): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    // Background with glossy border
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = textColor;
    ctx.lineWidth = 6;
    ctx.strokeRect(4, 4, width - 8, height - 8);

    // Accent line
    ctx.fillStyle = textColor;
    ctx.fillRect(16, height - 16, width - 32, 4);

    // Main text
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 36px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(text, width / 2, 54);

    // Sub text
    ctx.fillStyle = textColor;
    ctx.font = 'bold 20px sans-serif';
    ctx.fillText(subText, width / 2, 92);
  }
  const texture = new THREE.CanvasTexture(canvas);
  return texture;
}

export interface FactorySceneHandles {
  scene: THREE.Scene;
  animate: (delta: number) => void;
  dispose: () => void;
  setRoofMode: (mode: 'hidden' | 'truss' | 'solid' | 'xray') => void;
  setLightingIntensity: (intensity: number) => void;
  setAmrRoutesVisible: (visible: boolean) => void;
  setLabelsVisible: (visible: boolean) => void;
  setGridVisible: (visible: boolean) => void;
  setSafetyZonesVisible: (visible: boolean) => void;
  equipmentObjects: Map<string, THREE.Object3D>;
  interactiveMeshes: THREE.Mesh[];
  amrEntities: {
    id: string;
    object: THREE.Group;
    data: typeof AMR_FLEET_DATA[0];
    pathIndex: number;
    progress: number;
    speed: number;
  }[];
  slidingDoors: {
    wallX: number;
    doorLeft: THREE.Mesh;
    doorRight: THREE.Mesh;
    isOpen: boolean;
    openRatio: number;
  }[];
  getAmrPosition: (amrId: string) => THREE.Vector3 | null;
}

export interface BuildFactorySceneOptions {
  includeDemoAmrs?: boolean;
}

export function buildFactoryScene(
  { includeDemoAmrs = false }: BuildFactorySceneOptions = {},
): FactorySceneHandles {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#0f172a'); // Deep slate blue sky
  scene.fog = new THREE.FogExp2('#0f172a', 0.005);

  const equipmentObjects = new Map<string, THREE.Object3D>();
  const interactiveMeshes: THREE.Mesh[] = [];
  const roofGroups: THREE.Group[] = [];
  const trussGroups: THREE.Group[] = [];
  const labelGroups: THREE.Group[] = [];
  const amrRouteLines: THREE.Line[] = [];
  const highbayLights: THREE.Light[] = [];
  const safetyZoneMeshes: THREE.Mesh[] = [];
  let gridHelper: THREE.GridHelper | null = null;

  // 1. LIGHTING SETUP
  const ambientLight = new THREE.AmbientLight('#ffffff', 0.85);
  scene.add(ambientLight);

  const sunLight = new THREE.DirectionalLight('#ffffff', 1.2);
  sunLight.position.set(60, 50, 40);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.width = 1024;
  sunLight.shadow.mapSize.height = 1024;
  sunLight.shadow.camera.near = 0.5;
  sunLight.shadow.camera.far = 200;
  sunLight.shadow.camera.left = -70;
  sunLight.shadow.camera.right = 70;
  sunLight.shadow.camera.top = 70;
  sunLight.shadow.camera.bottom = -70;
  sunLight.shadow.bias = -0.0005;
  scene.add(sunLight);

  const hemiLight = new THREE.HemisphereLight('#93c5fd', '#334155', 0.4);
  scene.add(hemiLight);

  // 2. GROUND & OUTSIDE ENVIRONMENT
  const worldGroundGeo = new THREE.PlaneGeometry(300, 200);
  const worldGroundMat = new THREE.MeshStandardMaterial({
    color: '#1e293b',
    roughness: 0.9,
    metalness: 0.1,
  });
  const worldGround = new THREE.Mesh(worldGroundGeo, worldGroundMat);
  worldGround.rotation.x = -Math.PI / 2;
  worldGround.position.set(60, -0.05, 0);
  worldGround.receiveShadow = true;
  scene.add(worldGround);

  // Concrete exterior aprons for loading/shipping
  const dockApronGeo = new THREE.PlaneGeometry(16, 34);
  const dockApronMat = new THREE.MeshStandardMaterial({ color: '#334155', roughness: 0.8 });
  
  // Dock A exterior apron
  const apronA = new THREE.Mesh(dockApronGeo, dockApronMat);
  apronA.rotation.x = -Math.PI / 2;
  apronA.position.set(-8, 0, 0);
  scene.add(apronA);

  // Dock C exterior apron
  const apronC = new THREE.Mesh(dockApronGeo, dockApronMat);
  apronC.rotation.x = -Math.PI / 2;
  apronC.position.set(128, 0, 0);
  scene.add(apronC);

  // Semi-truck trailers parked at Receiving Dock A
  function createTruckTrailer(x: number, z: number, color: string) {
    const truckGroup = new THREE.Group();
    // Trailer body (13.6m long x 2.5m wide x 3.2m high)
    const bodyGeo = new THREE.BoxGeometry(12, 3.2, 2.5);
    const bodyMat = new THREE.MeshStandardMaterial({ color, roughness: 0.4 });
    const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
    bodyMesh.position.set(0, 2.2, 0);
    bodyMesh.castShadow = true;
    truckGroup.add(bodyMesh);

    // Chassis & Wheels
    const wheelMat = new THREE.MeshStandardMaterial({ color: '#111827', roughness: 0.9 });
    for (let wx = -4; wx <= 4; wx += 2.5) {
      const wheelL = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 0.4, 16), wheelMat);
      wheelL.rotation.x = Math.PI / 2;
      wheelL.position.set(wx, 0.5, 1.2);
      truckGroup.add(wheelL);

      const wheelR = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 0.4, 16), wheelMat);
      wheelR.rotation.x = Math.PI / 2;
      wheelR.position.set(wx, 0.5, -1.2);
      truckGroup.add(wheelR);
    }

    // Cab
    const cabGeo = new THREE.BoxGeometry(3, 3, 2.4);
    const cabMat = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.3 });
    const cabMesh = new THREE.Mesh(cabGeo, cabMat);
    cabMesh.position.set(-7.5, 2.1, 0);
    cabMesh.castShadow = true;
    truckGroup.add(cabMesh);

    truckGroup.position.set(x, 0, z);
    return truckGroup;
  }

  scene.add(createTruckTrailer(-8, -6, '#2563eb'));
  scene.add(createTruckTrailer(-8, 6, '#0284c7'));
  scene.add(createTruckTrailer(128, -6, '#10b981'));
  scene.add(createTruckTrailer(128, 6, '#059669'));

  // 3. FACTORY INTERIOR ZONES (A, B, C)
  const hazardTex = createHazardTexture();
  hazardTex.repeat.set(10, 1);

  // Common Wall Material
  const wallMat = new THREE.MeshStandardMaterial({
    color: '#f8fafc',
    roughness: 0.6,
    metalness: 0.1,
  });

  const wallMatWithStripes = new THREE.MeshStandardMaterial({
    color: '#e2e8f0',
    roughness: 0.5,
  });

  const glassDoorMat = new THREE.MeshStandardMaterial({
    color: '#93c5fd',
    transparent: true,
    opacity: 0.35,
    roughness: 0.22,
    metalness: 0.08,
  });

  // BUILD ZONE FLOORS AND PERIMETER WALLS
  FACTORY_ZONES.forEach((zone) => {
    const { length, width, height, xStart, zStart, xEnd, zEnd } = zone.dimensions;
    const centerX = (xStart + xEnd) / 2;
    const centerZ = (zStart + zEnd) / 2;

    // Floor
    const floorTex = createFloorGridTexture(zone.floorColor, 'rgba(255,255,255,0.08)', 256);
    floorTex.repeat.set(length / 2, width / 2);
    const floorMat = new THREE.MeshStandardMaterial({
      map: floorTex,
      roughness: 0.5,
      metalness: 0.2,
    });
    const floorGeo = new THREE.PlaneGeometry(length, width);
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.position.set(centerX, 0.01, centerZ);
    floorMesh.receiveShadow = true;
    scene.add(floorMesh);

    // North Wall (Z = -width/2)
    const northWallGeo = new THREE.BoxGeometry(length, height, 0.3);
    const northWall = new THREE.Mesh(northWallGeo, wallMat);
    northWall.position.set(centerX, height / 2, zStart);
    northWall.castShadow = true;
    northWall.receiveShadow = true;
    scene.add(northWall);

    // South Wall (Z = +width/2)
    const southWallGeo = new THREE.BoxGeometry(length, height, 0.3);
    const southWall = new THREE.Mesh(southWallGeo, wallMat);
    southWall.position.set(centerX, height / 2, zEnd);
    southWall.castShadow = true;
    southWall.receiveShadow = true;
    scene.add(southWall);

    // Sub-zone colored boundary outlines
    if (zone.subZones) {
      zone.subZones.forEach((sub) => {
        const { x, z, w, d } = sub.bounds;
        const subFloorGeo = new THREE.PlaneGeometry(w, d);
        const subFloorMat = new THREE.MeshBasicMaterial({
          color: sub.color,
          transparent: true,
          opacity: 0.12,
          side: THREE.DoubleSide
        });
        const subFloor = new THREE.Mesh(subFloorGeo, subFloorMat);
        subFloor.rotation.x = -Math.PI / 2;
        subFloor.position.set(x, 0.02, z);
        scene.add(subFloor);
        safetyZoneMeshes.push(subFloor);

        // Border line around subzone
        const points = [
          new THREE.Vector3(x - w / 2, 0.03, z - d / 2),
          new THREE.Vector3(x + w / 2, 0.03, z - d / 2),
          new THREE.Vector3(x + w / 2, 0.03, z + d / 2),
          new THREE.Vector3(x - w / 2, 0.03, z + d / 2),
          new THREE.Vector3(x - w / 2, 0.03, z - d / 2),
        ];
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
        const lineMat = new THREE.LineBasicMaterial({ color: sub.color, linewidth: 2 });
        const line = new THREE.Line(lineGeo, lineMat);
        scene.add(line);
        safetyZoneMeshes.push(line as unknown as THREE.Mesh);
      });
    }

    // Overhead Hanging Zone Signboard
    const signGroup = new THREE.Group();
    const signTex = createSignTexture(zone.code, `${zone.name} (${length}m × ${width}m)`, '#0f172a', '#38bdf8', 512, 128);
    const signGeo = new THREE.PlaneGeometry(8, 2);
    const signMat = new THREE.MeshBasicMaterial({ map: signTex, side: THREE.DoubleSide });
    const signMesh = new THREE.Mesh(signGeo, signMat);
    signMesh.position.set(0, 0, 0);
    signGroup.add(signMesh);

    // Suspension wires
    const wireMat = new THREE.MeshBasicMaterial({ color: '#64748b' });
    const wire1 = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 2.5), wireMat);
    wire1.position.set(-3.5, 1.25, 0);
    const wire2 = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 2.5), wireMat);
    wire2.position.set(3.5, 1.25, 0);
    signGroup.add(wire1, wire2);

    signGroup.position.set(centerX, height - 1.8, 0);
    scene.add(signGroup);
    labelGroups.push(signGroup);

    // High-bay industrial ceiling lights
    const lightsGroup = new THREE.Group();
    const lightRows = 3;
    const lightCols = Math.floor(length / 8);
    for (let c = 1; c <= lightCols; c++) {
      for (let r = 1; r <= lightRows; r++) {
        const lx = xStart + (c * length) / (lightCols + 1);
        const lz = zStart + (r * width) / (lightRows + 1);

        // Fixture mesh (UFO high bay)
        const fixtureGeo = new THREE.CylinderGeometry(0.4, 0.5, 0.2, 16);
        const fixtureMat = new THREE.MeshStandardMaterial({ color: '#0f172a', metalness: 0.8, roughness: 0.2 });
        const fixture = new THREE.Mesh(fixtureGeo, fixtureMat);
        fixture.position.set(lx, height - 0.5, lz);
        lightsGroup.add(fixture);

        // Glowing emitter face
        const glowGeo = new THREE.CircleGeometry(0.38, 16);
        const glowMat = new THREE.MeshBasicMaterial({ color: '#fef08a' });
        const glow = new THREE.Mesh(glowGeo, glowMat);
        glow.rotation.x = Math.PI / 2;
        glow.position.set(lx, height - 0.61, lz);
        lightsGroup.add(glow);

        // Point light for illumination
        if (c === Math.ceil(lightCols / 2) && r === 2) {
          const ptLight = new THREE.PointLight('#fffbeb', 0.6, 18, 1.5);
          ptLight.position.set(lx, height - 1.2, lz);
          scene.add(ptLight);
          highbayLights.push(ptLight);
        }
      }
    }
    scene.add(lightsGroup);

    // Steel Truss Roof Frame
    const trussGroup = new THREE.Group();
    const trussMat = new THREE.MeshStandardMaterial({
      color: '#475569',
      metalness: 0.6,
      roughness: 0.4,
    });

    const roofMeshGroup = new THREE.Group();
    // Solid roof panels (corrugated style)
    const roofGeo = new THREE.PlaneGeometry(length, width);
    const roofMat = new THREE.MeshStandardMaterial({
      color: '#334155',
      roughness: 0.8,
      metalness: 0.2,
      side: THREE.DoubleSide,
    });
    const roofMesh = new THREE.Mesh(roofGeo, roofMat);
    roofMesh.rotation.x = Math.PI / 2;
    roofMesh.position.set(centerX, height, centerZ);
    roofMeshGroup.add(roofMesh);

    // Structural trusses (space frame)
    for (let tx = xStart; tx <= xEnd; tx += 6) {
      // Main cross beam
      const beamGeo = new THREE.BoxGeometry(0.3, 0.4, width);
      const beam = new THREE.Mesh(beamGeo, trussMat);
      beam.position.set(tx, height - 0.2, centerZ);
      trussGroup.add(beam);

      // Support Columns at outer edges
      const colGeo = new THREE.BoxGeometry(0.4, height, 0.4);
      const colN = new THREE.Mesh(colGeo, trussMat);
      colN.position.set(tx, height / 2, zStart + 0.2);
      const colS = new THREE.Mesh(colGeo, trussMat);
      colS.position.set(tx, height / 2, zEnd - 0.2);
      trussGroup.add(colN, colS);

      // Diagonal cross webbings
      for (let tz = zStart + 3; tz < zEnd; tz += 6) {
        const diagGeo = new THREE.CylinderGeometry(0.06, 0.06, 4.2);
        const diag1 = new THREE.Mesh(diagGeo, trussMat);
        diag1.rotation.z = Math.PI / 4;
        diag1.position.set(tx, height - 0.6, tz);
        trussGroup.add(diag1);
      }
    }

    scene.add(trussGroup);
    scene.add(roofMeshGroup);
    trussGroups.push(trussGroup);
    roofGroups.push(roofMeshGroup);
  });

  // 4. END WALLS & PARTITIONS
  // End Wall A (X = 0) with 2 Loading Dock Doors
  const endWallAGroup = new THREE.Group();
  const wallA1 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 8, 8), wallMat);
  wallA1.position.set(0, 4, -11);
  const wallA2 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 8, 8), wallMat);
  wallA2.position.set(0, 4, 0);
  const wallA3 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 8, 8), wallMat);
  wallA3.position.set(0, 4, 11);
  const wallATop1 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 3.5, 4), wallMat);
  wallATop1.position.set(0, 6.25, -6);
  const wallATop2 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 3.5, 4), wallMat);
  wallATop2.position.set(0, 6.25, 6);
  endWallAGroup.add(wallA1, wallA2, wallA3, wallATop1, wallATop2);

  // Rollup doors at Dock A
  const rollupMat = new THREE.MeshStandardMaterial({ color: '#0284c7', metalness: 0.5, roughness: 0.3 });
  const dockDoorA1 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 4.5, 3.8), rollupMat);
  dockDoorA1.position.set(0, 2.25, -6);
  const dockDoorA2 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 4.5, 3.8), rollupMat);
  dockDoorA2.position.set(0, 2.25, 6);
  endWallAGroup.add(dockDoorA1, dockDoorA2);
  scene.add(endWallAGroup);

  // End Wall C (X = 120) with 2 Shipping Dock Doors
  const endWallCGroup = new THREE.Group();
  const wallC1 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 8, 8), wallMat);
  wallC1.position.set(120, 4, -11);
  const wallC2 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 8, 8), wallMat);
  wallC2.position.set(120, 4, 0);
  const wallC3 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 8, 8), wallMat);
  wallC3.position.set(120, 4, 11);
  const wallCTop1 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 3.5, 4), wallMat);
  wallCTop1.position.set(120, 6.25, -6);
  const wallCTop2 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 3.5, 4), wallMat);
  wallCTop2.position.set(120, 6.25, 6);
  endWallCGroup.add(wallC1, wallC2, wallC3, wallCTop1, wallCTop2);

  const dockDoorC1 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 4.5, 3.8), rollupMat);
  dockDoorC1.position.set(120, 2.25, -6);
  const dockDoorC2 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 4.5, 3.8), rollupMat);
  dockDoorC2.position.set(120, 2.25, 6);
  endWallCGroup.add(dockDoorC1, dockDoorC2);
  scene.add(endWallCGroup);

  // 5. INTER-ZONE PARTITION WALLS WITH AUTOMATIC SLIDING DOORS
  const slidingDoors: FactorySceneHandles['slidingDoors'] = [];

  function createInterzonePartition(wallX: number, heightLeft: number, heightRight: number) {
    const wallH = Math.max(heightLeft, heightRight);
    const partitionGroup = new THREE.Group();

    // North side partition (Z = -20 to -2)
    const partNorth = new THREE.Mesh(new THREE.BoxGeometry(0.3, wallH, 18), wallMatWithStripes);
    partNorth.position.set(wallX, wallH / 2, -11);

    // South side partition (Z = 2 to 20)
    const partSouth = new THREE.Mesh(new THREE.BoxGeometry(0.3, wallH, 18), wallMatWithStripes);
    partSouth.position.set(wallX, wallH / 2, 11);

    // Top lintel above door opening (Z = -2 to 2, Y = 4.5 to wallH)
    const partTop = new THREE.Mesh(new THREE.BoxGeometry(0.3, wallH - 4.5, 4.2), wallMatWithStripes);
    partTop.position.set(wallX, 4.5 + (wallH - 4.5) / 2, 0);

    partitionGroup.add(partNorth, partSouth, partTop);

    // Automatic Sliding Doors (4m total width, 4.5m high)
    const doorLeft = new THREE.Mesh(new THREE.BoxGeometry(0.1, 4.4, 2.0), glassDoorMat);
    doorLeft.position.set(wallX, 2.2, -1.0);

    const doorRight = new THREE.Mesh(new THREE.BoxGeometry(0.1, 4.4, 2.0), glassDoorMat);
    doorRight.position.set(wallX, 2.2, 1.0);

    partitionGroup.add(doorLeft, doorRight);
    scene.add(partitionGroup);

    // Overhead Door Sensor & Indicator
    const sensorGeo = new THREE.BoxGeometry(0.4, 0.3, 1.2);
    const sensorMat = new THREE.MeshBasicMaterial({ color: '#10b981' });
    const sensor = new THREE.Mesh(sensorGeo, sensorMat);
    sensor.position.set(wallX, 4.6, 0);
    scene.add(sensor);

    slidingDoors.push({
      wallX,
      doorLeft,
      doorRight,
      isOpen: false,
      openRatio: 0,
    });
  }

  // Partition between Zone A (8m) and Zone B (10m) at X = 40m
  createInterzonePartition(40, 8, 10);
  // Partition between Zone B (10m) and Zone C (8m) at X = 90m
  createInterzonePartition(90, 10, 8);

  // 6. AMR LANE FLOOR MARKINGS (4m wide highway in Zone B + aisles in Zone A & C)
  const laneMat = new THREE.MeshBasicMaterial({ color: '#facc15', side: THREE.DoubleSide });

  // Main 4m Central AMR Highway lines in Zone B (X=40 to 90, Z = -2 and +2)
  function createFloorStripe(x1: number, z1: number, x2: number, z2: number, width = 0.2) {
    const length = Math.hypot(x2 - x1, z2 - z1);
    const angle = Math.atan2(z2 - z1, x2 - x1);
    const stripeGeo = new THREE.PlaneGeometry(length, width);
    const stripe = new THREE.Mesh(stripeGeo, laneMat);
    stripe.rotation.x = -Math.PI / 2;
    stripe.rotation.z = angle;
    stripe.position.set((x1 + x2) / 2, 0.025, (z1 + z2) / 2);
    scene.add(stripe);
  }

  // Zone B Main Highway Striping (Double yellow border for 4m lane)
  createFloorStripe(40, -2, 90, -2, 0.2);
  createFloorStripe(40, 2, 90, 2, 0.2);
  // Dashed center line in Zone B
  for (let sx = 42; sx < 88; sx += 4) {
    createFloorStripe(sx, 0, sx + 2, 0, 0.15);
  }

  // Aisle striping in Zone A (3m aisles between 4 racks)
  createFloorStripe(10, -6, 36, -6, 0.15);
  createFloorStripe(10, 0, 36, 0, 0.15);
  createFloorStripe(10, 6, 36, 6, 0.15);

  // Zone C Shipping Lane Striping
  createFloorStripe(90, -2, 116, -2, 0.2);
  createFloorStripe(90, 2, 116, 2, 0.2);

  // 7. DETAILED INDUSTRIAL EQUIPMENT MESHES & PROCEDURAL ASSETS
  // 7A: PALLET RACKING (Zone A - 4 Rows, 6.5m High, Blue uprights RAL 5015 + Orange beams)
  const rackBlueMat = new THREE.MeshStandardMaterial({ color: '#1d4ed8', metalness: 0.5, roughness: 0.4 });
  const rackOrangeMat = new THREE.MeshStandardMaterial({ color: '#ea580c', metalness: 0.4, roughness: 0.5 });
  const woodPalletMat = new THREE.MeshStandardMaterial({ color: '#b45309', roughness: 0.8 });
  const batteryCellMat = new THREE.MeshStandardMaterial({ color: '#0f766e', metalness: 0.7, roughness: 0.3 });
  const cartonMat = new THREE.MeshStandardMaterial({ color: '#d97706', roughness: 0.9 });
  const metalCrateMat = new THREE.MeshStandardMaterial({ color: '#64748b', metalness: 0.8, roughness: 0.3 });

  function buildPalletRack(id: string, name: string, x: number, z: number, length = 16, height = 6.5, depth = 2.2) {
    const rackGroup = new THREE.Group();
    rackGroup.userData = { id, name, type: 'rack' };

    const uprightCols = Math.floor(length / 2.5);
    const tiers = 4;

    // Upright frames (X-braced)
    for (let i = 0; i <= uprightCols; i++) {
      const rx = -length / 2 + (i * length) / uprightCols;
      // Front & Back vertical columns
      const colGeo = new THREE.BoxGeometry(0.12, height, 0.12);
      const colF = new THREE.Mesh(colGeo, rackBlueMat);
      colF.position.set(rx, height / 2, depth / 2);
      const colB = new THREE.Mesh(colGeo, rackBlueMat);
      colB.position.set(rx, height / 2, -depth / 2);
      rackGroup.add(colF, colB);

      // Horizontal cross braces
      for (let t = 1; t <= tiers; t++) {
        const th = (t * height) / tiers;
        const braceGeo = new THREE.BoxGeometry(0.08, 0.08, depth);
        const brace = new THREE.Mesh(braceGeo, rackBlueMat);
        brace.position.set(rx, th, 0);
        rackGroup.add(brace);
      }
    }

    // Horizontal Orange Load Beams & Pallets with cargo
    for (let t = 1; t <= tiers; t++) {
      const th = (t * height) / tiers;
      // Front beam
      const beamF = new THREE.Mesh(new THREE.BoxGeometry(length, 0.15, 0.08), rackOrangeMat);
      beamF.position.set(0, th, depth / 2);
      // Back beam
      const beamB = new THREE.Mesh(new THREE.BoxGeometry(length, 0.15, 0.08), rackOrangeMat);
      beamB.position.set(0, th, -depth / 2);
      rackGroup.add(beamF, beamB);

      // Place pallets on this tier
      for (let p = 0; p < uprightCols; p++) {
        const px = -length / 2 + (p + 0.5) * (length / uprightCols);
        // Wooden pallet base
        const pallet = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.14, 1.0), woodPalletMat);
        pallet.position.set(px, th + 0.07, 0);
        pallet.castShadow = true;
        rackGroup.add(pallet);

        // Pallet payload (EV battery packs / metal crates / components)
        const randPayload = (p + t) % 3;
        if (randPayload === 0) {
          // EV Battery Module Stack
          const battBox = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.8, 0.9), batteryCellMat);
          battBox.position.set(px, th + 0.14 + 0.4, 0);
          battBox.castShadow = true;
          rackGroup.add(battBox);
        } else if (randPayload === 1) {
          // Metal Crate with EV chassis parts
          const crate = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.7, 0.9), metalCrateMat);
          crate.position.set(px, th + 0.14 + 0.35, 0);
          crate.castShadow = true;
          rackGroup.add(crate);
        } else {
          // Electronics Cartons
          const carton = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.9, 0.8), cartonMat);
          carton.position.set(px, th + 0.14 + 0.45, 0);
          carton.castShadow = true;
          rackGroup.add(carton);
        }
      }
    }

    // Bounding Box for interaction
    const hitBoxGeo = new THREE.BoxGeometry(length, height, depth + 0.4);
    const hitBoxMat = new THREE.MeshBasicMaterial({ visible: false });
    const hitBox = new THREE.Mesh(hitBoxGeo, hitBoxMat);
    hitBox.position.set(0, height / 2, 0);
    hitBox.userData = { equipmentId: id };
    rackGroup.add(hitBox);
    interactiveMeshes.push(hitBox);

    rackGroup.position.set(x, 0, z);
    scene.add(rackGroup);
    equipmentObjects.set(id, rackGroup);
    return rackGroup;
  }

  // Generate 4 Rows of Racking in Zone A (X=20, Z = -9, -3, +3, +9)
  buildPalletRack('rack-a-row1', 'Dãy Kệ K1 - Module Pin (Battery Packs)', 20, -9, 16, 6.5, 2.2);
  buildPalletRack('rack-a-row2', 'Dãy Kệ K2 - Động Cơ & Hộp Số (Motors)', 20, -3, 16, 6.5, 2.2);
  buildPalletRack('rack-a-row3', 'Dãy Kệ K3 - Khung Gầm & Treo (Chassis)', 20, 3, 16, 6.5, 2.2);
  buildPalletRack('rack-a-row4', 'Dãy Kệ K4 - Nội Thất & Dây Điện (Wiring)', 20, 9, 16, 6.5, 2.2);

  // 7B: INSPECTION AREA (Zone A)
  const inspectGroup = new THREE.Group();
  const inspectId = 'inspect-a';
  inspectGroup.userData = { id: inspectId };
  // Workstation tables & scanner arch
  const tableGeo = new THREE.BoxGeometry(4.5, 0.9, 1.8);
  const tableMat = new THREE.MeshStandardMaterial({ color: '#475569', metalness: 0.3 });
  const table = new THREE.Mesh(tableGeo, tableMat);
  table.position.set(12, 0.45, 8);
  inspectGroup.add(table);

  // 3D Optical Scanner Arch
  const archMat = new THREE.MeshStandardMaterial({ color: '#eab308', metalness: 0.6 });
  const arch1 = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.8, 0.2), archMat);
  arch1.position.set(10.5, 1.4, 8);
  const arch2 = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.8, 0.2), archMat);
  arch2.position.set(13.5, 1.4, 8);
  const archTop = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.2, 0.2), archMat);
  archTop.position.set(12, 2.8, 8);
  inspectGroup.add(arch1, arch2, archTop);

  // Scanner laser line
  const laserMat = new THREE.MeshBasicMaterial({ color: '#22c55e', transparent: true, opacity: 0.6 });
  const laserPlane = new THREE.Mesh(new THREE.PlaneGeometry(3.0, 2.0), laserMat);
  laserPlane.position.set(12, 1.4, 8);
  inspectGroup.add(laserPlane);

  const inspectHitBox = new THREE.Mesh(new THREE.BoxGeometry(6, 3, 4), new THREE.MeshBasicMaterial({ visible: false }));
  inspectHitBox.position.set(12, 1.5, 8);
  inspectHitBox.userData = { equipmentId: inspectId };
  inspectGroup.add(inspectHitBox);
  interactiveMeshes.push(inspectHitBox);

  scene.add(inspectGroup);
  equipmentObjects.set(inspectId, inspectGroup);

  // 7C: GIGA-PRESS DIE CASTING MACHINE (Zone B - X=50, Z=-11)
  const castingGroup = new THREE.Group();
  const castingId = 'casting-press-1';
  castingGroup.userData = { id: castingId };

  // Main Press Machine Body (12m x 6m x 7m)
  const pressBase = new THREE.Mesh(new THREE.BoxGeometry(11, 1.2, 5.5), new THREE.MeshStandardMaterial({ color: '#1e293b', metalness: 0.7 }));
  pressBase.position.set(50, 0.6, -11);
  castingGroup.add(pressBase);

  // Hydraulic Platen & Cylinders (Industrial heavy machine look)
  const platenMat = new THREE.MeshStandardMaterial({ color: '#f97316', metalness: 0.6, roughness: 0.3 });
  const platenRear = new THREE.Mesh(new THREE.BoxGeometry(2.5, 5.0, 5.0), platenMat);
  platenRear.position.set(45.5, 3.5, -11);
  const platenFront = new THREE.Mesh(new THREE.BoxGeometry(2.5, 5.0, 5.0), platenMat);
  platenFront.position.set(54.5, 3.5, -11);
  castingGroup.add(platenRear, platenFront);

  // Heavy Tie Bars (4 massive steel cylinders)
  const tieBarMat = new THREE.MeshStandardMaterial({ color: '#94a3b8', metalness: 0.9, roughness: 0.1 });
  const tieBarGeo = new THREE.CylinderGeometry(0.25, 0.25, 11, 16);
  const tb1 = new THREE.Mesh(tieBarGeo, tieBarMat);
  tb1.rotation.z = Math.PI / 2;
  tb1.position.set(50, 5.2, -13);
  const tb2 = new THREE.Mesh(tieBarGeo, tieBarMat);
  tb2.rotation.z = Math.PI / 2;
  tb2.position.set(50, 5.2, -9);
  const tb3 = new THREE.Mesh(tieBarGeo, tieBarMat);
  tb3.rotation.z = Math.PI / 2;
  tb3.position.set(50, 1.8, -13);
  const tb4 = new THREE.Mesh(tieBarGeo, tieBarMat);
  tb4.rotation.z = Math.PI / 2;
  tb4.position.set(50, 1.8, -9);
  castingGroup.add(tb1, tb2, tb3, tb4);

  // Die Mold & Molten Aluminum Injector Chamber
  const moldMesh = new THREE.Mesh(new THREE.BoxGeometry(3.0, 3.5, 4.0), new THREE.MeshStandardMaterial({ color: '#334155', metalness: 0.8 }));
  moldMesh.position.set(50, 3.5, -11);
  castingGroup.add(moldMesh);

  // Cooling Quench Tank & Conveyor
  const quenchTank = new THREE.Mesh(new THREE.BoxGeometry(3.5, 1.5, 3.5), new THREE.MeshStandardMaterial({ color: '#0284c7', metalness: 0.4 }));
  quenchTank.position.set(58, 0.75, -11);
  const quenchWater = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 3.2), new THREE.MeshStandardMaterial({ color: '#38bdf8', roughness: 0.1, metalness: 0.8 }));
  quenchWater.rotation.x = -Math.PI / 2;
  quenchWater.position.set(58, 1.45, -11);
  castingGroup.add(quenchTank, quenchWater);

  // Cast EV Underbody parts on cooling rack
  const castPartMat = new THREE.MeshStandardMaterial({ color: '#cbd5e1', metalness: 0.8, roughness: 0.2 });
  const castPart1 = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.2, 1.6), castPartMat);
  castPart1.position.set(58, 1.7, -11);
  castingGroup.add(castPart1);

  // Hitbox
  const castHitBox = new THREE.Mesh(new THREE.BoxGeometry(14, 7, 7), new THREE.MeshBasicMaterial({ visible: false }));
  castHitBox.position.set(51, 3.5, -11);
  castHitBox.userData = { equipmentId: castingId };
  castingGroup.add(castHitBox);
  interactiveMeshes.push(castHitBox);

  scene.add(castingGroup);
  equipmentObjects.set(castingId, castingGroup);

  // 7D: ROBOTIC WELDING CELLS (Zone B - X=70 & 78, Z=-13)
  const robotArmAnimatedList: {
    baseGroup: THREE.Group;
    joint1: THREE.Group;
    joint2: THREE.Group;
    torch: THREE.Mesh;
    sparkEmitter: THREE.Points;
    sparkLight: THREE.PointLight;
  }[] = [];

  function buildRoboticWelder(id: string, name: string, x: number, z: number) {
    const welderGroup = new THREE.Group();
    welderGroup.userData = { id, name, type: 'robot_welder' };

    // Pedestal
    const baseMat = new THREE.MeshStandardMaterial({ color: '#1e293b', metalness: 0.7 });
    const pedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.9, 0.8, 16), baseMat);
    pedestal.position.set(0, 0.4, 0);
    welderGroup.add(pedestal);

    // Robot Yellow Base Turntable
    const kukaMat = new THREE.MeshStandardMaterial({ color: '#ea580c', metalness: 0.4, roughness: 0.4 });
    const robotBase = new THREE.Group();
    robotBase.position.set(0, 0.8, 0);
    const turnTable = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 0.4, 16), kukaMat);
    robotBase.add(turnTable);

    // Lower Arm (Joint 1)
    const joint1 = new THREE.Group();
    joint1.position.set(0, 0.3, 0);
    const arm1 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.8, 0.4), kukaMat);
    arm1.position.set(0, 0.9, 0);
    joint1.add(arm1);

    // Upper Arm (Joint 2)
    const joint2 = new THREE.Group();
    joint2.position.set(0, 1.8, 0);
    const arm2 = new THREE.Mesh(new THREE.BoxGeometry(0.25, 1.6, 0.3), kukaMat);
    arm2.position.set(0, 0.8, 0);
    joint2.add(arm2);

    // Welding Torch Tool
    const toolMat = new THREE.MeshStandardMaterial({ color: '#334155', metalness: 0.9 });
    const torch = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.04, 0.5, 12), toolMat);
    torch.rotation.x = Math.PI / 2;
    torch.position.set(0, 1.6, 0.2);
    joint2.add(torch);

    joint1.add(joint2);
    robotBase.add(joint1);
    welderGroup.add(robotBase);

    // Welding Sparks Particles
    const sparkCount = 24;
    const sparkGeo = new THREE.BufferGeometry();
    const sparkPos = new Float32Array(sparkCount * 3);
    for (let s = 0; s < sparkCount * 3; s++) sparkPos[s] = (Math.random() - 0.5) * 0.4;
    sparkGeo.setAttribute('position', new THREE.BufferAttribute(sparkPos, 3));
    const sparkMat = new THREE.PointsMaterial({
      color: '#60a5fa',
      size: 0.12,
      transparent: true,
      blending: THREE.AdditiveBlending
    });
    const sparkEmitter = new THREE.Points(sparkGeo, sparkMat);
    sparkEmitter.position.set(0, 1.6, 0.6);
    joint2.add(sparkEmitter);

    const sparkLight = new THREE.PointLight('#60a5fa', 1.8, 8);
    sparkLight.position.set(0, 1.6, 0.6);
    joint2.add(sparkLight);

    // Safety Screen Enclosure (Amber tint)
    const screenMat = new THREE.MeshStandardMaterial({
      color: '#f59e0b',
      transparent: true,
      opacity: 0.45,
      roughness: 0.2,
      side: THREE.DoubleSide
    });
    const screenGeo = new THREE.BoxGeometry(3.6, 2.8, 0.1);
    const screenMesh = new THREE.Mesh(screenGeo, screenMat);
    screenMesh.position.set(0, 1.4, 2.2);
    welderGroup.add(screenMesh);

    // Fixture Jig table with EV car frame piece
    const jigTable = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.8, 1.8), baseMat);
    jigTable.position.set(0, 0.4, 1.2);
    welderGroup.add(jigTable);

    const evFramePiece = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.4, 1.2), new THREE.MeshStandardMaterial({ color: '#94a3b8', metalness: 0.7 }));
    evFramePiece.position.set(0, 0.95, 1.2);
    welderGroup.add(evFramePiece);

    // Hitbox
    const hitBox = new THREE.Mesh(new THREE.BoxGeometry(4.5, 4.5, 4.5), new THREE.MeshBasicMaterial({ visible: false }));
    hitBox.position.set(0, 2.0, 0.5);
    hitBox.userData = { equipmentId: id };
    welderGroup.add(hitBox);
    interactiveMeshes.push(hitBox);

    welderGroup.position.set(x, 0, z);
    scene.add(welderGroup);
    equipmentObjects.set(id, welderGroup);

    robotArmAnimatedList.push({
      baseGroup: robotBase,
      joint1,
      joint2,
      torch,
      sparkEmitter,
      sparkLight
    });

    return welderGroup;
  }

  buildRoboticWelder('welding-robot-1', 'Robot Hàn Tự Động #01', 70, -13);
  buildRoboticWelder('welding-robot-2', 'Robot Hàn Tự Động #02', 78, -13);

  // Connecting Conveyor Belt between Robot 1 and Robot 2
  const weldConvGeo = new THREE.BoxGeometry(8.0, 0.6, 1.4);
  const weldConvMat = new THREE.MeshStandardMaterial({ color: '#334155', metalness: 0.8 });
  const weldConv = new THREE.Mesh(weldConvGeo, weldConvMat);
  weldConv.position.set(74, 0.3, -11.8);
  scene.add(weldConv);

  // 7E: FINAL ASSEMBLY U-LINE (Zone B - 5 Sequential Stations in U-Shape)
  // Track Coordinates:
  // St1: (52, 14) -> St2: (62, 14) -> St3: (74, 14) -> St4: (82, 8) -> St5: (70, 4)
  const assemblyConveyorMat = new THREE.MeshStandardMaterial({ color: '#1e293b', metalness: 0.8 });
  const carPaintMat = new THREE.MeshStandardMaterial({ color: '#2563eb', metalness: 0.9, roughness: 0.2 });
  const glassMat = new THREE.MeshStandardMaterial({ color: '#38bdf8', roughness: 0.18, metalness: 0.15, transparent: true, opacity: 0.55 });
  const wheelMat = new THREE.MeshStandardMaterial({ color: '#09090b', roughness: 0.9 });

  // Procedural EV Vehicle Model Generator (Progressive stages)
  function createEVCarModel(stage: 1 | 2 | 3 | 4 | 5) {
    const carGroup = new THREE.Group();

    // Stage 1: Skateboard Chassis + Battery Pack Tray
    const skateboard = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.3, 1.8), new THREE.MeshStandardMaterial({ color: '#475569', metalness: 0.8 }));
    skateboard.position.set(0, 0.35, 0);
    carGroup.add(skateboard);

    const battTray = new THREE.Mesh(new THREE.BoxGeometry(2.8, 0.25, 1.4), batteryCellMat);
    battTray.position.set(0, 0.55, 0);
    carGroup.add(battTray);

    if (stage >= 2) {
      // Stage 2: Wheels & Suspension Axles
      for (const wx of [-1.4, 1.4]) {
        for (const wz of [-0.95, 0.95]) {
          const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.38, 0.25, 16), wheelMat);
          wheel.rotation.x = Math.PI / 2;
          wheel.position.set(wx, 0.38, wz);
          carGroup.add(wheel);
        }
      }
    }

    if (stage >= 3) {
      // Stage 3: Interior Cockpit Dashboard & Seats
      const cockpit = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.6, 1.4), new THREE.MeshStandardMaterial({ color: '#111827' }));
      cockpit.position.set(0.2, 0.85, 0);
      carGroup.add(cockpit);
      // Screen display
      const oledScreen = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.3, 0.6), new THREE.MeshBasicMaterial({ color: '#38bdf8' }));
      oledScreen.position.set(0.6, 1.1, 0);
      carGroup.add(oledScreen);
    }

    if (stage >= 4) {
      // Stage 4: Sleek Body Frame & Pillars
      const carBody = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.9, 1.9), carPaintMat);
      carBody.position.set(0, 0.95, 0);
      carBody.castShadow = true;
      carGroup.add(carBody);

      // Cabin Roof & Glass
      const cabinRoof = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.6, 1.6), glassMat);
      cabinRoof.position.set(-0.2, 1.5, 0);
      carGroup.add(cabinRoof);
    }

    if (stage >= 5) {
      // Stage 5: Headlights, Taillights & Glossy Finished Details
      const headLightL = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.15, 0.4), new THREE.MeshBasicMaterial({ color: '#ffffff' }));
      headLightL.position.set(2.2, 0.95, 0.6);
      const headLightR = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.15, 0.4), new THREE.MeshBasicMaterial({ color: '#ffffff' }));
      headLightR.position.set(2.2, 0.95, -0.6);
      carGroup.add(headLightL, headLightR);

      // LED Light bar in rear
      const tailLight = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.1, 1.6), new THREE.MeshBasicMaterial({ color: '#ef4444' }));
      tailLight.position.set(-2.2, 1.0, 0);
      carGroup.add(tailLight);
    }

    return carGroup;
  }

  // Build the 5 Workstations with Overhead Gantries & Tooling
  const stationDefs = [
    { id: 'assembly-st1', name: 'Trạm 1: Pin & Khung Gầm (Battery Marriage)', pos: [52, 14] as [number, number], stage: 1 as const },
    { id: 'assembly-st2', name: 'Trạm 2: Trục & Phanh (Suspension & Axles)', pos: [62, 14] as [number, number], stage: 2 as const },
    { id: 'assembly-st3', name: 'Trạm 3: Taplo & Nội Thất (Cockpit Integration)', pos: [74, 14] as [number, number], stage: 3 as const },
    { id: 'assembly-st4', name: 'Trạm 4: Thân Vỏ & Kính Nóc (Body Panels & Glass)', pos: [82, 8] as [number, number], stage: 4 as const },
    { id: 'assembly-st5', name: 'Trạm 5: Bánh Xe & Kích Hoạt Điện (Wheels & Power-On)', pos: [70, 4] as [number, number], stage: 5 as const },
  ];

  stationDefs.forEach((st) => {
    const stGroup = new THREE.Group();
    stGroup.userData = { id: st.id, name: st.name, type: 'assembly_station' };

    // Conveyor section bed
    const convBed = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.4, 2.6), assemblyConveyorMat);
    convBed.position.set(st.pos[0], 0.2, st.pos[1]);
    stGroup.add(convBed);

    // Industrial Overhead Gantry (Yellow steel arch)
    const gantryMat = new THREE.MeshStandardMaterial({ color: '#eab308', metalness: 0.6 });
    const postL = new THREE.Mesh(new THREE.BoxGeometry(0.2, 4.0, 0.2), gantryMat);
    postL.position.set(st.pos[0] - 2.8, 2.0, st.pos[1] - 1.8);
    const postR = new THREE.Mesh(new THREE.BoxGeometry(0.2, 4.0, 0.2), gantryMat);
    postR.position.set(st.pos[0] - 2.8, 2.0, st.pos[1] + 1.8);
    const beamTop = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.3, 3.8), gantryMat);
    beamTop.position.set(st.pos[0] - 2.8, 4.0, st.pos[1]);
    stGroup.add(postL, postR, beamTop);

    // Tooling balancer & LED task lighting
    const toolHead = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.8), new THREE.MeshStandardMaterial({ color: '#0284c7' }));
    toolHead.position.set(st.pos[0] - 2.8, 2.6, st.pos[1]);
    stGroup.add(toolHead);

    // Station Name Billboard
    const stSign = new THREE.Mesh(
      new THREE.PlaneGeometry(3.2, 0.6),
      new THREE.MeshBasicMaterial({ map: createSignTexture(`STATION #${st.stage}`, st.name.split(':')[0], '#0f172a', '#10b981', 256, 64), side: THREE.DoubleSide })
    );
    stSign.position.set(st.pos[0], 3.8, st.pos[1]);
    stGroup.add(stSign);

    // Vehicle at this assembly stage
    const car = createEVCarModel(st.stage);
    car.position.set(st.pos[0], 0.4, st.pos[1]);
    if (st.stage === 4) car.rotation.y = -Math.PI / 2;
    if (st.stage === 5) car.rotation.y = Math.PI;
    stGroup.add(car);

    // HitBox
    const hitBox = new THREE.Mesh(new THREE.BoxGeometry(7, 4.5, 4.5), new THREE.MeshBasicMaterial({ visible: false }));
    hitBox.position.set(st.pos[0], 2.2, st.pos[1]);
    hitBox.userData = { equipmentId: st.id };
    stGroup.add(hitBox);
    interactiveMeshes.push(hitBox);

    scene.add(stGroup);
    equipmentObjects.set(st.id, stGroup);
  });

  // Connective U-shaped conveyor segments
  function addConveyorSegment(x: number, z: number, w: number, d: number, rotY = 0) {
    const seg = new THREE.Mesh(new THREE.BoxGeometry(w, 0.4, d), assemblyConveyorMat);
    seg.position.set(x, 0.2, z);
    seg.rotation.y = rotY;
    scene.add(seg);
  }
  // Connect 1->2->3
  addConveyorSegment(57, 14, 4, 2.6);
  addConveyorSegment(68, 14, 6, 2.6);
  // Curve 3->4
  addConveyorSegment(78, 11, 2.6, 5);
  // Curve 4->5
  addConveyorSegment(76, 4, 6, 2.6);

  // 7F: FINAL QC STATIONS (Zone C - Red Striped Inspection Zone)
  function buildQCStation(id: string, name: string, x: number, z: number, type: 'adas' | 'dyno') {
    const qcGroup = new THREE.Group();
    qcGroup.userData = { id, name, type: 'qc_station' };

    // Red safety perimeter border
    const redBorder = new THREE.Mesh(
      new THREE.PlaneGeometry(7.0, 4.5),
      new THREE.MeshBasicMaterial({ color: '#dc2626', transparent: true, opacity: 0.2, side: THREE.DoubleSide })
    );
    redBorder.rotation.x = -Math.PI / 2;
    redBorder.position.set(x, 0.03, z);
    qcGroup.add(redBorder);

    // Floor outline line
    const pnts = [
      new THREE.Vector3(x - 3.5, 0.04, z - 2.25),
      new THREE.Vector3(x + 3.5, 0.04, z - 2.25),
      new THREE.Vector3(x + 3.5, 0.04, z + 2.25),
      new THREE.Vector3(x - 3.5, 0.04, z + 2.25),
      new THREE.Vector3(x - 3.5, 0.04, z - 2.25),
    ];
    const borderLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pnts), new THREE.LineBasicMaterial({ color: '#ef4444', linewidth: 3 }));
    scene.add(borderLine);

    if (type === 'adas') {
      // ADAS Laser Calibration Targets
      const targetMat = new THREE.MeshStandardMaterial({ color: '#ffffff', metalness: 0.2 });
      const targetStandL = new THREE.Mesh(new THREE.BoxGeometry(0.1, 2.2, 1.2), targetMat);
      targetStandL.position.set(x + 3.2, 1.1, z - 1.2);
      const targetStandR = new THREE.Mesh(new THREE.BoxGeometry(0.1, 2.2, 1.2), targetMat);
      targetStandR.position.set(x + 3.2, 1.1, z + 1.2);
      qcGroup.add(targetStandL, targetStandR);

      // Laser beams
      const beamGeo = new THREE.CylinderGeometry(0.01, 0.01, 6.0);
      const beamMat = new THREE.MeshBasicMaterial({ color: '#ef4444' });
      const b1 = new THREE.Mesh(beamGeo, beamMat);
      b1.rotation.z = Math.PI / 2;
      b1.position.set(x, 0.8, z - 0.8);
      const b2 = new THREE.Mesh(beamGeo, beamMat);
      b2.rotation.z = Math.PI / 2;
      b2.position.set(x, 0.8, z + 0.8);
      qcGroup.add(b1, b2);
    } else {
      // Dynamometer Dual Roller Bed
      const rollerMat = new THREE.MeshStandardMaterial({ color: '#334155', metalness: 0.9, roughness: 0.2 });
      for (const rx of [x - 1.4, x + 1.4]) {
        const roller = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 2.4, 24), rollerMat);
        roller.rotation.x = Math.PI / 2;
        roller.position.set(rx, 0.15, z);
        qcGroup.add(roller);
      }
    }

    // Fully assembled finished EV under test
    const evInTest = createEVCarModel(5);
    evInTest.position.set(x, 0.05, z);
    qcGroup.add(evInTest);

    // Hitbox
    const hitBox = new THREE.Mesh(new THREE.BoxGeometry(7.5, 4.0, 5.0), new THREE.MeshBasicMaterial({ visible: false }));
    hitBox.position.set(x, 2.0, z);
    hitBox.userData = { equipmentId: id };
    qcGroup.add(hitBox);
    interactiveMeshes.push(hitBox);

    scene.add(qcGroup);
    equipmentObjects.set(id, qcGroup);
  }

  buildQCStation('qc-station-1', 'Trạm QC #01: ADAS & Góc Lái (Wheel Alignment)', 98, -5, 'adas');
  buildQCStation('qc-station-2', 'Trạm QC #02: Băng Thử Dynamometer & Phanh', 98, 5, 'dyno');

  // Finished EV Staging Buffer in Zone C (EVs ready to ship)
  for (let row = 0; row < 2; row++) {
    for (let col = 0; col < 3; col++) {
      const finishedEV = createEVCarModel(5);
      finishedEV.position.set(106 + col * 4.5, 0.05, -9 + row * 4.5);
      scene.add(finishedEV);
    }
  }

  // 8. AMR FLEET CREATION & REALTIME PATH ANIMATION
  const amrEntities: FactorySceneHandles['amrEntities'] = [];

  function buildAMRMesh(data: typeof AMR_FLEET_DATA[0]) {
    const amrGroup = new THREE.Group();
    amrGroup.userData = { id: data.id, name: data.name, type: 'amr' };

    // AMR Body Chassis (1.4m x 0.45m x 1.0m)
    const bodyMat = new THREE.MeshStandardMaterial({ color: data.color, metalness: 0.6, roughness: 0.3 });
    const body = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.4, 1.0), bodyMat);
    body.position.set(0, 0.25, 0);
    body.castShadow = true;
    amrGroup.add(body);

    // Black Bumper & Skirts
    const bumper = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.15, 1.1), new THREE.MeshStandardMaterial({ color: '#09090b', roughness: 0.9 }));
    bumper.position.set(0, 0.1, 0);
    amrGroup.add(bumper);

    // Rotating 3D LiDAR Puck Sensor
    const lidarMat = new THREE.MeshStandardMaterial({ color: '#1e293b', metalness: 0.9 });
    const lidar = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.15, 16), lidarMat);
    lidar.position.set(0.5, 0.52, 0);
    amrGroup.add(lidar);

    // Flashing Green / Amber Status Beacon
    const beacon = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.12), new THREE.MeshBasicMaterial({ color: '#22c55e' }));
    beacon.position.set(-0.5, 0.52, 0);
    amrGroup.add(beacon);

    // AMR Payload (Pallet on top)
    const payloadPallet = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.1, 0.9), woodPalletMat);
    payloadPallet.position.set(0, 0.5, 0);
    amrGroup.add(payloadPallet);

    // Specific Cargo payload
    const cargo = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.4, 0.7), new THREE.MeshStandardMaterial({ color: '#0284c7', metalness: 0.6 }));
    cargo.position.set(0, 0.75, 0);
    amrGroup.add(cargo);

    // Hitbox
    const hitBox = new THREE.Mesh(new THREE.BoxGeometry(1.8, 1.2, 1.4), new THREE.MeshBasicMaterial({ visible: false }));
    hitBox.position.set(0, 0.6, 0);
    hitBox.userData = { equipmentId: data.id };
    amrGroup.add(hitBox);
    interactiveMeshes.push(hitBox);

    // Render path guide line
    const pathPoints = data.path.map(p => new THREE.Vector3(p.x, 0.05, p.z));
    const pathGeo = new THREE.BufferGeometry().setFromPoints(pathPoints);
    const pathLine = new THREE.Line(pathGeo, new THREE.LineDashedMaterial({ color: data.color, dashSize: 0.8, gapSize: 0.4 }));
    pathLine.computeLineDistances();
    scene.add(pathLine);
    amrRouteLines.push(pathLine);

    scene.add(amrGroup);
    equipmentObjects.set(data.id, amrGroup);

    return {
      id: data.id,
      object: amrGroup,
      data,
      pathIndex: 0,
      progress: 0,
      speed: 0.25,
    };
  }

  if (includeDemoAmrs) {
    AMR_FLEET_DATA.forEach((amrData) => {
      const amrEntity = buildAMRMesh(amrData);
      amrEntities.push(amrEntity);
    });
  }

  // 9. METRIC 1:1 GRID HELPER
  gridHelper = new THREE.GridHelper(140, 140, '#38bdf8', '#334155');
  gridHelper.position.set(60, 0.02, 0);
  scene.add(gridHelper);

  // ANIMATION LOOP UPDATE
  let time = 0;
  function animate(delta: number) {
    time += delta;

    // 1. Robot Welding Sparks & Movement
    robotArmAnimatedList.forEach((robot, idx) => {
      const offset = idx * 2.0;
      const angle1 = Math.sin(time * 1.5 + offset) * 0.4;
      const angle2 = Math.cos(time * 2.0 + offset) * 0.3 - 0.2;
      robot.joint1.rotation.z = angle1;
      robot.joint2.rotation.z = angle2;
      robot.baseGroup.rotation.y = Math.sin(time * 0.8 + offset) * 0.5;

      // Spark flicker
      const isSparking = Math.sin(time * 4 + offset) > -0.2;
      robot.sparkEmitter.visible = isSparking;
      robot.sparkLight.intensity = isSparking ? (1.5 + Math.random() * 2.0) : 0;
      if (isSparking) {
        const positions = robot.sparkEmitter.geometry.attributes.position.array as Float32Array;
        for (let i = 0; i < positions.length; i += 3) {
          positions[i] = (Math.random() - 0.5) * 0.5;
          positions[i + 1] = Math.random() * 0.4;
          positions[i + 2] = (Math.random() - 0.5) * 0.5;
        }
        robot.sparkEmitter.geometry.attributes.position.needsUpdate = true;
      }
    });

    // 2. AMR Fleet Movement & Navigation
    amrEntities.forEach((amr) => {
      const path = amr.data.path;
      if (path.length < 2) return;

      const p1 = path[amr.pathIndex];
      const nextIdx = (amr.pathIndex + 1) % path.length;
      const p2 = path[nextIdx];

      const dx = p2.x - p1.x;
      const dz = p2.z - p1.z;
      const segDist = Math.hypot(dx, dz) || 1;

      amr.progress += (amr.speed * delta * 4) / segDist;

      if (amr.progress >= 1) {
        amr.progress = 0;
        amr.pathIndex = nextIdx;
      }

      const curX = p1.x + dx * amr.progress;
      const curZ = p1.z + dz * amr.progress;
      amr.object.position.set(curX, 0, curZ);

      // Target rotation facing next waypoint
      const targetAngle = Math.atan2(dz, dx);
      amr.object.rotation.y = -targetAngle;
    });

    // 3. Automatic Sliding Doors check proximity to AMRs
    slidingDoors.forEach((door) => {
      // Check if any AMR is within 5m of door
      let shouldOpen = false;
      amrEntities.forEach((amr) => {
        const dist = Math.abs(amr.object.position.x - door.wallX);
        const distZ = Math.abs(amr.object.position.z);
        if (dist < 6.0 && distZ < 3.0) {
          shouldOpen = true;
        }
      });

      if (shouldOpen) {
        door.openRatio = Math.min(1, door.openRatio + delta * 2.5);
      } else {
        door.openRatio = Math.max(0, door.openRatio - delta * 1.5);
      }

      // Slide left door towards -Z, right door towards +Z
      door.doorLeft.position.z = -1.0 - door.openRatio * 1.6;
      door.doorRight.position.z = 1.0 + door.openRatio * 1.6;
    });
  }

  function getAmrPosition(amrId: string): THREE.Vector3 | null {
    const amr = amrEntities.find(a => a.id === amrId);
    return amr ? amr.object.position : null;
  }

  function setRoofMode(mode: 'hidden' | 'truss' | 'solid' | 'xray') {
    if (mode === 'hidden') {
      roofGroups.forEach(g => g.visible = false);
      trussGroups.forEach(g => g.visible = false);
    } else if (mode === 'truss') {
      roofGroups.forEach(g => g.visible = false);
      trussGroups.forEach(g => g.visible = true);
    } else if (mode === 'solid') {
      roofGroups.forEach(g => {
        g.visible = true;
        g.traverse(child => {
          if (child instanceof THREE.Mesh && child.material) {
            child.material.transparent = false;
            child.material.opacity = 1.0;
          }
        });
      });
      trussGroups.forEach(g => g.visible = true);
    } else if (mode === 'xray') {
      roofGroups.forEach(g => {
        g.visible = true;
        g.traverse(child => {
          if (child instanceof THREE.Mesh && child.material) {
            child.material.transparent = true;
            child.material.opacity = 0.2;
          }
        });
      });
      trussGroups.forEach(g => g.visible = true);
    }
  }

  function setLightingIntensity(intensity: number) {
    ambientLight.intensity = 0.85 * intensity;
    sunLight.intensity = 1.2 * intensity;
    highbayLights.forEach(l => l.intensity = 0.6 * intensity);
  }

  function setAmrRoutesVisible(visible: boolean) {
    amrRouteLines.forEach(l => l.visible = visible);
  }

  function setLabelsVisible(visible: boolean) {
    labelGroups.forEach(l => l.visible = visible);
  }

  function setGridVisible(visible: boolean) {
    if (gridHelper) gridHelper.visible = visible;
  }

  function setSafetyZonesVisible(visible: boolean) {
    safetyZoneMeshes.forEach(m => m.visible = visible);
  }

  function dispose() {
    scene.traverse((object) => {
      if (!(object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.Points)) {
        return;
      }
      object.geometry.dispose();
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach((material) => {
        Object.values(material).forEach((value) => {
          if (value instanceof THREE.Texture) value.dispose();
        });
        material.dispose();
      });
    });
    scene.clear();
  }

  // Keep the interior visible and avoid rendering hundreds of roof/truss draw calls.
  setRoofMode('hidden');

  return {
    scene,
    animate,
    dispose,
    setRoofMode,
    setLightingIntensity,
    setAmrRoutesVisible,
    setLabelsVisible,
    setGridVisible,
    setSafetyZonesVisible,
    equipmentObjects,
    interactiveMeshes,
    amrEntities,
    slidingDoors,
    getAmrPosition
  };
}
