import { GLBViewer } from '../components/GLBViewer';

export function Viewer() {
  // Load the test.glb from public directory or relative path
  const modelUrl = '/test.glb';

  return (
    <div className="w-full h-screen">
      <GLBViewer modelUrl={modelUrl} />
    </div>
  );
}
