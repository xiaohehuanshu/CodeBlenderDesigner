"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF, Environment } from "@react-three/drei";
import { useStore } from "@/store";

/* ------------------------------------------------------------------ */
/* GLB model loader                                                   */
/* ------------------------------------------------------------------ */

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

function Scene({ url }: { url: string }) {
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 10, 5]} intensity={0.8} castShadow />
      <Model url={url} />
      <OrbitControls makeDefault enableDamping dampingFactor={0.1} />
      <Environment preset="city" />
    </>
  );
}

function EmptyScene() {
  return (
    <>
      <ambientLight intensity={0.4} />
      <gridHelper args={[20, 20, "#888", "#444"]} />
      <OrbitControls makeDefault />
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Canvas wrapper                                                     */
/* ------------------------------------------------------------------ */

export default function Viewport() {
  const modelUrl = useStore((s) => s.modelUrl);

  return (
    <div className="flex-1 relative bg-zinc-950 rounded-lg overflow-hidden">
      <Suspense
        fallback={
          <div className="absolute inset-0 flex items-center justify-center text-zinc-400 text-sm">
            加载 3D 模型中…
          </div>
        }
      >
        <Canvas camera={{ position: [5, 5, 5], fov: 50 }} className="w-full h-full">
          {modelUrl ? <Scene url={modelUrl} /> : <EmptyScene />}
        </Canvas>
      </Suspense>
      {!modelUrl && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-zinc-500 text-sm">
            在左侧输入设计需求，生成 3D 模型后在此预览
          </p>
        </div>
      )}
    </div>
  );
}
