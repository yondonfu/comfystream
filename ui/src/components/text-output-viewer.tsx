import React, { useState, useEffect, useRef } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MessageSquare, Copy, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

interface TextOutputSegment {
  id: string;
  text: string;
  timestamp: Date;
  isProcessing?: boolean;
}

interface TextOutputViewerProps {
  isConnected: boolean;
  textOutputData?: string;
}

export const TextOutputViewer: React.FC<TextOutputViewerProps> = ({
  isConnected,
  textOutputData,
}) => {
  const [segments, setSegments] = useState<TextOutputSegment[]>([]);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [segments]);

  useEffect(() => {
    if (!textOutputData) return;

    try {
      let newSegments: TextOutputSegment[] = [];
      if (textOutputData.startsWith('[') || textOutputData.startsWith('{')) {
        const parsed = JSON.parse(textOutputData);
        if (Array.isArray(parsed)) {
          newSegments = parsed.map((item: any, index: number) => ({
            id: `${Date.now()}-${index}`,
            text: item.text || item.word || '',
            timestamp: new Date(),
          })).filter(seg => seg.text.trim() && !seg.text.includes('__WARMUP_SENTINEL__'));
        }
      } else if (typeof textOutputData === 'string' && textOutputData.trim()) {
        if (!textOutputData.includes('__WARMUP_SENTINEL__')) {
          newSegments = [{
            id: `${Date.now()}`,
            text: textOutputData.trim(),
            timestamp: new Date(),
          }];
        }
      }

      if (newSegments.length > 0) {
        setSegments(prev => [...newSegments, ...prev].slice(0, 50));
      }
    } catch (error) {
      console.error('Error parsing text output data:', error);
    }
  }, [textOutputData]);

  const copyAllText = () => {
    const allText = [...segments]
      .reverse()
      .map(seg => `[${formatTime(seg.timestamp)}] ${seg.text}`)
      .join('\n');
    navigator.clipboard.writeText(allText);
    toast.success('Text copied to clipboard');
  };

  const clearText = () => {
    setSegments([]);
    toast.success('Text cleared');
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <Card className="w-full bg-transparent border-0 shadow-none text-white">
      <CardHeader className="pb-3 space-y-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <div className="relative">
              <MessageSquare className="w-5 h-5" />
              {isConnected && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
              )}
            </div>
            Text Output Stream
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge 
              variant={isConnected ? "default" : "secondary"}
              className={isConnected ? "bg-green-600 text-white" : "bg-gray-600 text-gray-300"}
            >
              {isConnected ? "Connected" : "Disconnected"}
            </Badge>
          </div>
        </div>
        <div className="flex items-center justify-end pt-2">
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={copyAllText}
              disabled={segments.length === 0}
              className="text-xs text-gray-400 hover:text-gray-300"
            >
              <Copy className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearText}
              disabled={segments.length === 0}
              className="text-xs text-gray-400 hover:text-gray-300"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-0 flex-1 overflow-hidden">
        <ScrollArea className="h-[40vh] px-4" ref={scrollAreaRef}>
          <div className="space-y-3 pb-4">
            {segments.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">
                  {isConnected 
                    ? "Waiting for text output..."
                    : "Connect to start receiving text"
                  }
                </p>
              </div>
            ) : (
              segments.map((segment) => (
                <div
                  key={segment.id}
                  className="group relative bg-slate-800/50 rounded-lg p-3 border border-slate-700/50 hover:bg-slate-800/70 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-xs text-gray-400 font-mono mt-0.5 flex-shrink-0">
                      {formatTime(segment.timestamp)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white leading-relaxed break-words">
                        {segment.text}
                      </p>
                    </div>
                  </div>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(segment.text);
                      toast.success('Segment copied');
                    }}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 h-6 w-6 text-gray-400 hover:text-gray-300"
                  >
                    <Copy className="w-3 h-3" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};
