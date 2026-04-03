import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Environment, Grid } from '@react-three/drei';
import { Suspense } from 'react';

interface ModelProps {
  url: string;
}

function Model({ url }: ModelProps) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

interface GLBViewerProps {
  modelUrl: string;
}

export function GLBViewer({ modelUrl }: GLBViewerProps) {
  return (
    <div className="w-full h-screen bg-gray-900">
      <Canvas
        camera={{ position: [5, 5, 5], fov: 50 }}
        shadows
        dpr={[1, 2]}
      >
        <Suspense fallback={null}>
          {/* Lighting */}
          <ambientLight intensity={0.5} />
          <directionalLight
            position={[10, 10, 5]}
            intensity={1}
            castShadow
          />
          <pointLight position={[-10, -10, -5]} intensity={0.5} />

          {/* Model */}
          <Model url={modelUrl} />

          {/* Environment and helpers */}
          <Environment preset="studio" />
          <Grid
            args={[20, 20]}
            cellSize={1}
            cellThickness={0.5}
            cellColor="#6f6f6f"
            sectionSize={5}
            sectionThickness={1}
            sectionColor="#9d4b4b"
            fadeDistance={30}
            fadeStrength={1}
            followCamera={false}
            infiniteGrid
          />

          {/* Controls */}
          <OrbitControls
            makeDefault
            enableDamping
            dampingFactor={0.05}
            minDistance={1}
            maxDistance={50}
          />
        </Suspense>
      </Canvas>

      {/* Info overlay */}
      <div className="absolute top-4 left-4 bg-black/70 text-white px-4 py-2 rounded-lg">
        <p className="text-sm">Model: {modelUrl.split('/').pop()}</p>
        <p className="text-xs text-gray-400 mt-1">Drag to rotate • Scroll to zoom</p>
      </div>
    </div>
  );
}
