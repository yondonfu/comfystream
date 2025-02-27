// Read params directly from window.location.search
const cachedParams = typeof window !== 'undefined' ? (() => {
  console.log('Reading query params from:', window.location.search);
  const searchParams = new URLSearchParams(window.location.search);
  const frameRateParam = searchParams.get('frameRate');
  
  const params = {
    streamUrl: searchParams.get('streamUrl'),
    frameRate: frameRateParam ? parseInt(frameRateParam) : undefined,
    videoDevice: searchParams.get('videoDevice'),
    audioDevice: searchParams.get('audioDevice'),
    workflowUrl: searchParams.get('workflowUrl'),
    skipDialog: searchParams.get('skipDialog') === 'true'
  };
  console.log('Parsed params:', params);
  return params;
})() : {
  streamUrl: null,
  frameRate: undefined,
  videoDevice: null,
  audioDevice: null,
  workflowUrl: null,
  skipDialog: false
};

// Just return the cached params
export function useQueryParams() {
  console.log('useQueryParams called, returning:', cachedParams);
  return cachedParams;
} 