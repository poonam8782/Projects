'use client';

import { useState, useEffect, useCallback } from 'react';
import { ProtectedRoute } from '@/lib/auth/protected-route';
import { useAuth } from '@/lib/auth/auth-context';
import { motion } from 'framer-motion';
import {
  Button,
  Card,
  CardHeader,
  CardContent,
  CardFooter,
  Badge,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  Checkbox,
} from '@neura/ui';
import FileUploader from '@/components/FileUploader';
import TopNav from '@/components/TopNav';
import { DocumentMetadata, FlashcardResponse, ExportRequest, SynthesizeRequest, DocumentSource } from '@/lib/types/document';
import { formatFileSize, formatDate } from '@/lib/utils/format';
import { FileText, Download, Trash2, AlertCircle, Loader2, Eye, Sparkles, MessageSquare, FileDown, BookOpen, GraduationCap, FileArchive, Network } from 'lucide-react';
import { toast } from 'sonner';
import { getDocuments, deleteDocument as apiDeleteDocument, getDownloadUrl, embedDocument, generateNotes, generateMindmap, generateFlashcards, getFlashcardsByDocument, exportDocument, synthesizeDocuments, getNotes } from '@/services/api';
import MindmapViewer from '@/components/MindmapViewer';
import { useRouter } from 'next/navigation';
import { getFileTypeLabel, getStatusBadgeVariant } from '@/lib/utils/document';

// Loading animation variants
const barVariants = {
  initial: {
    scaleY: 0.5,
    opacity: 0,
  },
  animate: {
    scaleY: 1,
    opacity: 1,
    transition: {
      repeat: Infinity,
      repeatType: "mirror" as const,
      duration: 1,
      ease: "circIn",
    },
  },
};

// Bar Loader Component
const BarLoader = () => {
  return (
    <motion.div
      transition={{
        staggerChildren: 0.25,
      }}
      initial="initial"
      animate="animate"
      className="flex gap-1"
    >
      <motion.div variants={barVariants} className="h-12 w-2 bg-[#ff8800]" />
      <motion.div variants={barVariants} className="h-12 w-2 bg-[#ff8800]" />
      <motion.div variants={barVariants} className="h-12 w-2 bg-[#ff8800]" />
      <motion.div variants={barVariants} className="h-12 w-2 bg-[#ff8800]" />
      <motion.div variants={barVariants} className="h-12 w-2 bg-[#ff8800]" />
    </motion.div>
  );
};

// Loading Dialog Component
const LoadingDialog = ({ open, message }: { open: boolean; message: string }) => {
  return (
    <Dialog open={open}>
      <DialogContent className="sm:max-w-md bg-white border-0 shadow-2xl">
        <div className="flex flex-col items-center justify-center py-8 gap-6">
          <BarLoader />
          <p className="text-lg font-medium text-gray-700">{message}</p>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default function DashboardPage() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  
  // State management
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [flashcardMetadata, setFlashcardMetadata] = useState<Map<string, { count: number; nextReview: string | null }>>(new Map());
  const [notesMetadata, setNotesMetadata] = useState<Map<string, boolean>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<DocumentMetadata | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [embeddingDocuments, setEmbeddingDocuments] = useState<Set<string>>(new Set());
  const [generatingNotes, setGeneratingNotes] = useState<Set<string>>(new Set());
  const [generatingMindmaps, setGeneratingMindmaps] = useState<Set<string>>(new Set());
  const [generatingFlashcards, setGeneratingFlashcards] = useState<Set<string>>(new Set());
  const [notesDialogOpen, setNotesDialogOpen] = useState(false);
  const [mindmapDialogOpen, setMindmapDialogOpen] = useState(false);
  const [flashcardsDialogOpen, setFlashcardsDialogOpen] = useState(false);
  const [currentNotes, setCurrentNotes] = useState<{ content: string; filename: string; downloadUrl: string; documentId: string } | null>(null);
  const [currentMindmap, setCurrentMindmap] = useState<{ downloadUrl: string; filename: string; nodeCount: number | null } | null>(null);
  const [currentFlashcards, setCurrentFlashcards] = useState<{ documentId: string; flashcards: FlashcardResponse[]; count: number } | null>(null);
  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set());
  const [exportFormat, setExportFormat] = useState<'markdown' | 'pdf'>('markdown');
  const [exporting, setExporting] = useState(false);
  const [synthesisDialogOpen, setSynthesisDialogOpen] = useState(false);
  const [synthesisResult, setSynthesisResult] = useState<{ markdown: string; sources: DocumentSource[]; type: string } | null>(null);
  const [loadingDialogOpen, setLoadingDialogOpen] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('Processing...');

  const handleSignOut = async () => {
    await signOut();
    // ProtectedRoute will redirect when user becomes null
  };

  // Called by FileUploader after successful upload to refresh document list
  const fetchFlashcardMetadata = useCallback(async (documentIds: string[]) => {
    try {
      const metadata = new Map<string, { count: number; nextReview: string | null }>();
      const nowIso = new Date().toISOString();

      for (const documentId of documentIds) {
        try {
          const flashcards = await getFlashcardsByDocument(documentId);
          const count = flashcards.length;
          
          // Find earliest next_review (prefer due cards, then upcoming)
          let nextReview: string | null = null;
          if (flashcards.length > 0) {
            const dueCards = flashcards.filter(c => c.next_review <= nowIso);
            const cardsToCheck = dueCards.length > 0 ? dueCards : flashcards;
            const sortedCards = cardsToCheck.sort((a, b) => 
              a.next_review.localeCompare(b.next_review)
            );
            if (sortedCards.length > 0 && sortedCards[0]) {
              nextReview = sortedCards[0].next_review;
            }
          }

          metadata.set(documentId, { count, nextReview });
        } catch (err) {
          console.warn(`Failed to fetch flashcards for document ${documentId}:`, err);
          // Continue with other documents
        }
      }

      setFlashcardMetadata(metadata);
    } catch (err) {
      console.warn('Failed to fetch flashcard metadata:', err);
      // Don't fail the whole dashboard if metadata fetch fails
    }
  }, []);

  // Fetch notes existence for all documents
  const fetchNotesMetadata = useCallback(async (documentIds: string[]) => {
    try {
      // Parallel fetching with Promise.allSettled
      const promises = documentIds.map(async (documentId) => {
        try {
          const result = await getNotes(documentId);
          // null means 404 - notes don't exist
          if (result === null) {
            return { id: documentId, hasNotes: false };
          }
          return { id: documentId, hasNotes: true };
        } catch (err) {
          // For errors (401, 500, etc.), log warning and return undefined
          console.warn(`Failed to check notes for document ${documentId}:`, err);
          return { id: documentId, hasNotes: undefined };
        }
      });

      const results = await Promise.allSettled(promises);
      const metadata = new Map<string, boolean>();

      results.forEach((result) => {
        if (result.status === 'fulfilled' && result.value.hasNotes !== undefined) {
          metadata.set(result.value.id, result.value.hasNotes);
        }
      });

      setNotesMetadata(metadata);
    } catch (err) {
      console.warn('Failed to fetch notes metadata:', err);
      // Don't fail the whole dashboard if metadata fetch fails
    }
  }, []);

  // Fetch documents from backend
  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const documents = await getDocuments();
      setDocuments(documents);
      // Fetch both flashcard and notes metadata in parallel
      await Promise.all([
        fetchFlashcardMetadata(documents.map(d => d.id)),
        fetchNotesMetadata(documents.map(d => d.id))
      ]);
    } catch (err) {
      console.error('Error fetching documents:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load documents';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [fetchFlashcardMetadata, fetchNotesMetadata]);

  const handleUploadComplete = useCallback(() => {
    toast.success('Document uploaded successfully');
    void fetchDocuments();
  }, [fetchDocuments]);

  // Fetch documents on mount
  useEffect(() => {
    void fetchDocuments();
  }, [fetchDocuments]);

  // Clean up selection state when documents change (e.g., after deletion)
  useEffect(() => {
    const currentIds = new Set(documents.map(doc => doc.id));
    setSelectedDocuments(prev => new Set([...prev].filter(id => currentIds.has(id))));
  }, [documents]);

  // Handle delete button click
  const handleDelete = (document: DocumentMetadata) => {
    setDocumentToDelete(document);
    setDeleteDialogOpen(true);
  };

  // Confirm delete
  const confirmDelete = async () => {
    if (!documentToDelete) return;
    
    setDeleting(true);
    
    try {
      await apiDeleteDocument(documentToDelete.id);
      
      // Remove document from local state
      setDocuments(prev => prev.filter(d => d.id !== documentToDelete.id));
      toast.success('Document deleted successfully');
      setDeleteDialogOpen(false);
      setDocumentToDelete(null);
    } catch (err) {
      console.error('Error deleting document:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete document';
      toast.error(errorMessage);
    } finally {
      setDeleting(false);
    }
  };

  // Handle download
  const handleDownload = async (document: DocumentMetadata) => {
    try {
      const url = await getDownloadUrl(document.id);
      window.open(url, '_blank');
    } catch (err) {
      console.error('Error downloading document:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to download document';
      toast.error(errorMessage);
    }
  };

  // Handle open (same as download but explicit action)
  const handleOpen = async (document: DocumentMetadata) => {
    try {
      const url = await getDownloadUrl(document.id);
      window.open(url, '_blank');
    } catch (err) {
      console.error('Error opening document:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to open document';
      toast.error(errorMessage);
    }
  };

  // Handle embed
  const handleEmbed = async (document: DocumentMetadata) => {
    // Validate document status
    if (document.status !== 'extracted') {
      toast.error('Document must have extracted text before embedding');
      return;
    }

    // Add document ID to embedding set
    setEmbeddingDocuments(prev => new Set(prev).add(document.id));

    // Show loading toast
    const toastId = toast.loading('Generating embeddings...');

    try {
      // Call embed API
      const result = await embedDocument(document.id);

      // Dismiss loading toast
      toast.dismiss(toastId);

      // Compute safe duration string
      const durationString = typeof result.processing_time_seconds === 'number' 
        ? ` (${result.processing_time_seconds.toFixed(1)}s)` 
        : '';

      // Show success toast with processing time
      toast.success(`${result.message || 'Embeddings generated successfully'}${durationString}`);

      // Update local document state to reflect new status
      setDocuments(prev => prev.map(d => 
        d.id === document.id ? { ...d, status: 'embedded' as const } : d
      ));
    } catch (err) {
      // Dismiss loading toast
      toast.dismiss(toastId);

      // Extract error message
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate embeddings';

      // Show error toast
      toast.error(errorMessage);

      // Log error for debugging
      console.error('Error embedding document:', err);
    } finally {
      // Remove document ID from embedding set
      setEmbeddingDocuments(prev => {
        const next = new Set(prev);
        next.delete(document.id);
        return next;
      });
    }
  };

  // Navigate to future document detail page with chat
  const handleChat = (document: DocumentMetadata) => {
    if (document.status !== 'embedded') {
      toast.error('Document must be embedded before chatting');
      return;
    }
    // Placeholder navigation - detail page will host DocumentChat component in Sprint 3 Phase 2
  // Casting to string route for now pending detail page creation
    router.push(`/document/${document.id}`)
  };

  // Navigate to view notes page
  const handleViewNotes = (document: DocumentMetadata) => {
    router.push(`/notes/${document.id}`);
  };

  // Navigate to view flashcards page
  const handleViewFlashcards = (document: DocumentMetadata) => {
    router.push(`/flashcards/${document.id}/list`);
  };

  // Handle generate notes
  const handleGenerateNotes = async (document: DocumentMetadata) => {
    if (document.status === 'uploaded') {
      toast.error('Document must have extracted text before generating notes');
      return;
    }
    setGeneratingNotes(prev => new Set(prev).add(document.id));
    setLoadingMessage('Generating notes...');
    setLoadingDialogOpen(true);
    try {
      const result = await generateNotes(document.id);
      setLoadingDialogOpen(false);
      const duration = typeof result.processing_time_seconds === 'number' ? ` (${result.processing_time_seconds.toFixed(1)}s)` : '';
      toast.success(`Notes generated${duration}`);
      setCurrentNotes({
        content: result.content_preview || '',
        filename: result.filename,
        downloadUrl: result.download_url,
        documentId: document.id,
      });
      setNotesMetadata(prev => { const next = new Map(prev); next.set(document.id, true); return next; });
      setNotesDialogOpen(true);
    } catch (err) {
      setLoadingDialogOpen(false);
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate notes';
      toast.error(errorMessage);
      console.error('Error generating notes:', err);
    } finally {
      setGeneratingNotes(prev => {
        const next = new Set(prev);
        next.delete(document.id);
        return next;
      });
    }
  };

  // Handle generate mindmap
  const handleGenerateMindmap = async (document: DocumentMetadata) => {
    if (document.status === 'uploaded') {
      toast.error('Document must have extracted text before generating mindmap');
      return;
    }
    setGeneratingMindmaps(prev => new Set(prev).add(document.id));
    setLoadingMessage('Generating mindmap...');
    setLoadingDialogOpen(true);
    try {
      const result = await generateMindmap(document.id);
      setLoadingDialogOpen(false);
      const duration = typeof result.processing_time_seconds === 'number' ? ` (${result.processing_time_seconds.toFixed(1)}s)` : '';
      toast.success(`Mindmap generated${duration}`);
      setCurrentMindmap({
        downloadUrl: result.download_url,
        filename: result.filename,
        nodeCount: result.node_count || null,
      });
      setMindmapDialogOpen(true);
    } catch (err) {
      setLoadingDialogOpen(false);
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate mindmap';
      toast.error(errorMessage);
      console.error('Error generating mindmap:', err);
    } finally {
      setGeneratingMindmaps(prev => {
        const next = new Set(prev);
        next.delete(document.id);
        return next;
      });
    }
  };

  // Handle generate flashcards
  const handleGenerateFlashcards = async (document: DocumentMetadata) => {
    if (document.status === 'uploaded') {
      toast.error('Document must have extracted text before generating flashcards');
      return;
    }
    setGeneratingFlashcards(prev => new Set(prev).add(document.id));
    setLoadingMessage('Generating flashcards...');
    setLoadingDialogOpen(true);
    try {
      const result = await generateFlashcards(document.id, 10);
      setLoadingDialogOpen(false);
      toast.success(`${result.flashcard_count} flashcards generated (${result.processing_time_seconds.toFixed(1)}s)`);
      setCurrentFlashcards({
        documentId: document.id,
        flashcards: result.flashcards,
        count: result.flashcard_count,
      });
      setFlashcardMetadata(prev => { const next = new Map(prev); const nowIso = new Date().toISOString(); const flashcards = result.flashcards; const count = result.flashcard_count; const due = flashcards.filter(c => c.next_review <= nowIso); const pool = due.length > 0 ? due : flashcards; const nextReview = pool.length > 0 ? (pool.sort((a,b) => a.next_review.localeCompare(b.next_review))[0]?.next_review ?? null) : null; next.set(document.id, { count, nextReview }); return next; });
      setFlashcardsDialogOpen(true);
    } catch (err) {
      setLoadingDialogOpen(false);
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate flashcards';
      toast.error(errorMessage);
      console.error('Error generating flashcards:', err);
    } finally {
      setGeneratingFlashcards(prev => {
        const next = new Set(prev);
        next.delete(document.id);
        return next;
      });
    }
  };

  // Selection handlers
  const handleToggleSelect = (documentId: string) => {
    setSelectedDocuments(prev => {
      const next = new Set(prev);
      if (next.has(documentId)) {
        next.delete(documentId);
      } else {
        next.add(documentId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    setSelectedDocuments(new Set(documents.map(doc => doc.id)));
  };

  const handleDeselectAll = () => {
    setSelectedDocuments(new Set());
  };

  // Export handler
  const handleExport = async () => {
    // Validate selection
    if (selectedDocuments.size === 0) {
      toast.error('Please select at least one document');
      return;
    }

    // Validate maximum for synthesis
    if (selectedDocuments.size > 10) {
      toast.error('Maximum 10 documents for synthesis');
      return;
    }

    setExporting(true);

    try {
      if (selectedDocuments.size === 1) {
        // Single document export
        const documentId = Array.from(selectedDocuments)[0];
        if (!documentId) {
          toast.error('Invalid document selection');
          return;
        }
        setLoadingMessage('Exporting document...');
        setLoadingDialogOpen(true);

        const request: ExportRequest = {
          document_id: documentId,
          format: exportFormat,
          include_notes: true,
          include_flashcards: true,
          include_chat_history: false,
        };

        const result = await exportDocument(request);
        setLoadingDialogOpen(false);
        toast.success(`Export generated (${result.processing_time_seconds.toFixed(1)}s)`);
        window.open(result.download_url, '_blank');
        toast.info(`Included: ${result.included_sections.join(', ')}`);
        setSelectedDocuments(new Set());
      } else {
        // Multi-document synthesis
        // Validate all selected documents have extracted text
        const selectedDocIds = Array.from(selectedDocuments);
        const ineligibleDocs = selectedDocIds
          .map(id => documents.find(doc => doc.id === id))
          .filter(doc => doc && doc.status !== 'extracted' && doc.status !== 'embedded')
          .map(doc => doc?.filename);

        if (ineligibleDocs.length > 0) {
          toast.error(`Cannot synthesize: The following documents lack extracted text: ${ineligibleDocs.join(', ')}`);
          return;
        }

        setLoadingMessage(`Synthesizing ${selectedDocuments.size} documents...`);
        setLoadingDialogOpen(true);

        const request: SynthesizeRequest = {
          document_ids: selectedDocIds,
          synthesis_type: 'summary',
          include_embeddings: false,
        };

        const result = await synthesizeDocuments(request);
        setLoadingDialogOpen(false);
        toast.success(`Synthesis complete (${result.processing_time_seconds.toFixed(1)}s)`);
        setSynthesisResult({
          markdown: result.markdown_output,
          sources: result.sources,
          type: result.synthesis_type,
        });
        setSynthesisDialogOpen(true);
        setSelectedDocuments(new Set());
      }
    } catch (err) {
      setLoadingDialogOpen(false);
      const errorMessage = err instanceof Error ? err.message : 'Failed to export/synthesize documents';
      toast.error(errorMessage);
      console.error('Error exporting/synthesizing:', err);
    } finally {
      setExporting(false);
    }
  };

  // Download synthesis markdown
  const handleDownloadSynthesis = () => {
    if (!synthesisResult) return;

    const blob = new Blob([synthesisResult.markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `synthesis-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <ProtectedRoute>
      <TopNav />
      <main
        className="min-h-screen p-8"
        style={{
          background: "radial-gradient(circle at 15% 20%, #F6F5FF 0%, #FFF6EF 45%, #EDF7F0 100%)",
          color: "#111827"
        }}
      >
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold">Dashboard</h1>
            <p className="text-muted-ui text-sm">Signed in as {user?.email}</p>
          </div>
          <Button variant="outline" onClick={() => void handleSignOut()}>
            Sign Out
          </Button>
        </div>

        <div className="space-y-8">
          <div>
            <h2 className="text-2xl font-semibold text-text-ui mb-4">Upload Document</h2>
            <FileUploader onUploadComplete={handleUploadComplete} />
          </div>

          <div>
            <h2 className="text-2xl font-semibold text-text-ui mb-4">Your Documents</h2>
            
            {/* Export controls - only show when documents exist */}
            {documents.length > 0 && (
              <div className="flex items-center justify-between mb-4 p-4 bg-surface-ui border border-border-ui rounded-lg">
                <div className="flex items-center gap-4">
                  <span className="text-sm text-muted-ui">
                    {selectedDocuments.size} selected
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleSelectAll}
                    disabled={selectedDocuments.size === documents.length}
                  >
                    Select All
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDeselectAll}
                    disabled={selectedDocuments.size === 0}
                  >
                    Clear
                  </Button>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Button
                      variant={exportFormat === 'markdown' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setExportFormat('markdown')}
                    >
                      Markdown
                    </Button>
                    <Button
                      variant={exportFormat === 'pdf' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setExportFormat('pdf')}
                    >
                      PDF
                    </Button>
                  </div>
                  <Button
                    onClick={() => void handleExport()}
                    disabled={selectedDocuments.size === 0 || exporting}
                  >
                    {exporting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        {selectedDocuments.size === 1 ? 'Exporting...' : 'Synthesizing...'}
                      </>
                    ) : (
                      <>
                        <FileArchive className="w-4 h-4 mr-2" />
                        {selectedDocuments.size === 1 ? 'Export' : selectedDocuments.size > 1 ? 'Synthesize' : 'Export'}
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}
            
            {/* Loading state */}
            {loading && (
              <Card className="bg-surface-ui border-border-ui">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-muted-ui animate-spin mb-4" />
                  <p className="text-muted-ui">Loading documents...</p>
                </CardContent>
              </Card>
            )}

            {/* Error state */}
            {error && !loading && (
              <Card className="bg-surface-ui border-border-ui">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <AlertCircle className="w-8 h-8 text-muted-ui mb-4" />
                  <p className="text-muted-ui mb-4">{error}</p>
                  <Button variant="outline" onClick={() => void fetchDocuments()}>
                    Retry
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Empty state */}
            {!loading && !error && documents.length === 0 && (
              <Card className="bg-surface-ui border-border-ui">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <FileText className="w-12 h-12 text-muted-ui mb-4" />
                  <p className="text-muted-ui">No documents yet. Upload your first document above.</p>
                </CardContent>
              </Card>
            )}

            {/* Document grid */}
            {!loading && !error && documents.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {documents.map((document) => (
                  <Card
                    key={document.id}
                    className="bg-surface-ui border-border-ui hover:border-border-strong transition-colors"
                  >
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-2 flex-1 min-w-0">
                          <Checkbox
                            checked={selectedDocuments.has(document.id)}
                            onCheckedChange={() => handleToggleSelect(document.id)}
                            aria-label={`Select ${document.filename}`}
                            className="flex-shrink-0"
                          />
                          <FileText className="w-5 h-5 text-text-ui flex-shrink-0" />
                          <button
                            onClick={() => handleOpen(document)}
                            className="text-sm truncate text-left hover:underline focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded"
                            tabIndex={0}
                          >
                            {document.filename}
                          </button>
                        </div>
                        <Badge variant={getStatusBadgeVariant(document.status)}>
                          {document.status}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-ui">Size:</span>
                        <span className="text-text-ui">{formatFileSize(document.size_bytes)}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-ui">Uploaded:</span>
                        <span className="text-text-ui">{formatDate(document.created_at)}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-ui">Type:</span>
                        <Badge variant="outline" className="text-xs">
                          {getFileTypeLabel(document.mime_type)}
                        </Badge>
                      </div>
                      {flashcardMetadata.has(document.id) && flashcardMetadata.get(document.id)!.count > 0 && (
                        <>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-ui">Flashcards:</span>
                            <span className="text-text-ui">{flashcardMetadata.get(document.id)!.count} flashcards</span>
                          </div>
                          {(() => {
                            const metadata = flashcardMetadata.get(document.id);
                            const nextReview = metadata?.nextReview;
                            if (nextReview) {
                              return (
                                <div className="flex items-center justify-between text-sm">
                                  <span className="text-muted-ui">Next review:</span>
                                  <span className="text-text-ui">
                                    {nextReview <= new Date().toISOString()
                                      ? 'Due now'
                                      : formatDate(nextReview)}
                                  </span>
                                </div>
                              );
                            }
                            return null;
                          })()}
                        </>
                      )}
                    </CardContent>
                    <CardFooter className="flex justify-end space-x-2">
                      {(document.status === 'extracted' || document.status === 'embedded' || document.status === 'failed') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEmbed(document)}
                          disabled={embeddingDocuments.has(document.id) || document.status === 'embedded'}
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Generate embeddings for AI chat"
                          title="Generate embeddings for AI chat"
                        >
                          {embeddingDocuments.has(document.id) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Sparkles className="w-4 h-4" />
                          )}
                        </Button>
                      )}
                      {notesMetadata.get(document.id) === true && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewNotes(document)}
                          className="text-primary hover:text-primary/80"
                          aria-label="View notes"
                          title="View generated notes"
                        >
                          <BookOpen className="w-4 h-4" />
                        </Button>
                      )}
                      {(document.status === 'extracted' || document.status === 'embedded' || document.status === 'failed') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleGenerateNotes(document)}
                          disabled={generatingNotes.has(document.id)}
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Generate notes"
                          title="Generate study notes"
                        >
                          {generatingNotes.has(document.id) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <FileDown className="w-4 h-4" />
                          )}
                        </Button>
                      )}
                      {(document.status === 'extracted' || document.status === 'embedded' || document.status === 'failed') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleGenerateMindmap(document)}
                          disabled={generatingMindmaps.has(document.id)}
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Generate mindmap"
                          title="Generate mindmap"
                        >
                          {generatingMindmaps.has(document.id) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Network className="w-4 h-4" />
                          )}
                        </Button>
                      )}
                      {flashcardMetadata.has(document.id) && flashcardMetadata.get(document.id)!.count > 0 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewFlashcards(document)}
                          className="text-primary hover:text-primary/80"
                          aria-label="View flashcards"
                          title="View flashcard library"
                        >
                          <GraduationCap className="w-4 h-4" />
                        </Button>
                      )}
                      {(document.status === 'extracted' || document.status === 'embedded' || document.status === 'failed') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleGenerateFlashcards(document)}
                          disabled={generatingFlashcards.has(document.id)}
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Generate flashcards"
                          title="Generate flashcards"
                        >
                          {generatingFlashcards.has(document.id) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <GraduationCap className="w-4 h-4" />
                          )}
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpen(document)}
                        className="text-text-ui hover:text-text-ui"
                        aria-label="View document"
                        title="View document"
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(document)}
                        className="text-text-ui hover:text-text-ui"
                        aria-label="Download document"
                        title="Download document"
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                      {document.status === 'embedded' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleChat(document)}
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Chat with document"
                          title="Chat with document"
                        >
                          <MessageSquare className="w-4 h-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(document)}
                        className="text-muted-ui hover:text-text-ui"
                        aria-label="Delete document"
                        title="Delete document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </CardFooter>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Delete confirmation dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="bg-surface-ui border-border-ui">
            <DialogHeader>
              <DialogTitle>Delete Document</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete <strong>{documentToDelete?.filename}</strong>? This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => void confirmDelete()}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Notes preview dialog */}
        <Dialog open={notesDialogOpen} onOpenChange={setNotesDialogOpen}>
          <DialogContent className="bg-white dark:bg-surface-ui border-border-ui max-w-3xl">
            <DialogHeader>
              <DialogTitle className="text-2xl text-gray-900 dark:text-text-ui">
                📝 Study Notes Generated!
              </DialogTitle>
              <DialogDescription className="text-gray-600 dark:text-muted-ui">
                AI-generated study notes from your document
              </DialogDescription>
            </DialogHeader>
            {currentNotes && (
              <div className="py-4 space-y-4">
                {/* Notes preview */}
                <div className="max-h-[50vh] overflow-y-auto p-4 bg-gray-50 dark:bg-black-ui border border-gray-200 dark:border-border-ui rounded-lg">
                  <pre className="whitespace-pre-wrap text-sm text-gray-900 dark:text-text-ui font-mono leading-relaxed">
                    {currentNotes.content}
                  </pre>
                </div>
                
                {/* Info */}
                <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-muted-ui">
                  <span>📄 {currentNotes.filename}</span>
                </div>
              </div>
            )}
            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button
                variant="outline"
                size="lg"
                onClick={() => setNotesDialogOpen(false)}
                className="w-full sm:w-auto"
              >
                Close
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={() => currentNotes?.downloadUrl && window.open(currentNotes.downloadUrl, '_blank')}
                disabled={!currentNotes}
                className="w-full sm:w-auto"
              >
                📥 Download Markdown
              </Button>
              <Button
                variant="default"
                size="lg"
                onClick={() => {
                  // Extract document ID from the notes context
                  const docId = documents.find(d => 
                    currentNotes?.filename.includes(d.id) || 
                    currentNotes?.filename.includes(d.filename.replace(/\.[^/.]+$/, ''))
                  )?.id;
                  if (docId) {
                    setNotesDialogOpen(false);
                    router.push(`/notes/${docId}`);
                  }
                }}
                disabled={!currentNotes}
                className="w-full sm:w-auto bg-primary hover:bg-primary/90"
              >
                � View Full Notes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Mindmap viewer dialog */}
        <Dialog open={mindmapDialogOpen} onOpenChange={setMindmapDialogOpen}>
          <DialogContent className="bg-surface-ui border-border-ui max-w-6xl max-h-[90vh] overflow-hidden">
            <DialogHeader>
              <DialogTitle>{currentMindmap?.filename || 'Generated Mindmap'}</DialogTitle>
              <DialogDescription>Interactive mindmap visualization of your document structure.</DialogDescription>
            </DialogHeader>
            {currentMindmap && (
              <div className="mb-4">
                <MindmapViewer
                  downloadUrl={currentMindmap.downloadUrl}
                  documentName={currentMindmap.filename}
                  showControls
                  allowFullscreen
                  className="h-[600px]"
                />
              </div>
            )}
            <DialogFooter>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => currentMindmap?.downloadUrl && window.open(currentMindmap.downloadUrl, '_blank')}
                disabled={!currentMindmap}
              >
                Download SVG
              </Button>
              <Button variant="outline" size="sm" onClick={() => setMindmapDialogOpen(false)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Flashcards preview dialog */}
        <Dialog open={flashcardsDialogOpen} onOpenChange={setFlashcardsDialogOpen}>
          <DialogContent className="bg-white dark:bg-surface-ui border-border-ui max-w-xl">
            <DialogHeader>
              <DialogTitle className="text-2xl text-gray-900 dark:text-text-ui">
                ✨ Flashcards Generated!
              </DialogTitle>
              <DialogDescription className="text-gray-600 dark:text-muted-ui">
                {currentFlashcards?.count ? (
                  <>Successfully generated {currentFlashcards.count} flashcard{currentFlashcards.count !== 1 ? 's' : ''} from your document</>
                ) : (
                  'Your flashcards are ready'
                )}
              </DialogDescription>
            </DialogHeader>
            {currentFlashcards && currentFlashcards.flashcards.length > 0 && (
              <div className="py-6 space-y-4">
                {/* Sample flashcard preview */}
                <div className="bg-gray-50 dark:bg-black-ui border border-gray-200 dark:border-border-ui rounded-lg p-4">
                  <p className="text-xs text-gray-500 dark:text-muted-ui mb-2">Sample flashcard:</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-text-ui mb-2">
                    Q: {currentFlashcards.flashcards[0]?.question}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-muted-ui">
                    A: {currentFlashcards.flashcards[0]?.answer?.substring(0, 100)}
                    {(currentFlashcards.flashcards[0]?.answer?.length || 0) > 100 ? '...' : ''}
                  </p>
                </div>

                {/* Stats */}
                <div className="flex items-center justify-center gap-8 text-center py-4">
                  <div>
                    <p className="text-3xl font-bold text-gray-900 dark:text-text-ui">{currentFlashcards.count}</p>
                    <p className="text-xs text-gray-500 dark:text-muted-ui mt-1">Total Cards</p>
                  </div>
                  <div className="h-12 w-px bg-gray-200 dark:bg-border-ui" />
                  <div>
                    <p className="text-3xl font-bold text-gray-900 dark:text-text-ui">{currentFlashcards.count}</p>
                    <p className="text-xs text-gray-500 dark:text-muted-ui mt-1">Ready to Review</p>
                  </div>
                </div>
              </div>
            )}
            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button
                variant="outline"
                size="lg"
                onClick={() => setFlashcardsDialogOpen(false)}
                className="w-full sm:w-auto"
              >
                Close
              </Button>
              <Button
                variant="default"
                size="lg"
                onClick={() => {
                  setFlashcardsDialogOpen(false);
                  router.push(`/flashcards/${currentFlashcards?.documentId}`);
                }}
                disabled={!currentFlashcards || currentFlashcards.flashcards.length === 0}
                className="w-full sm:w-auto bg-primary hover:bg-primary/90"
              >
                <GraduationCap className="w-5 h-5 mr-2" />
                Start Practice Session
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Synthesis result dialog */}
        <Dialog open={synthesisDialogOpen} onOpenChange={setSynthesisDialogOpen}>
          <DialogContent className="bg-surface-ui border-border-ui max-w-4xl max-h-[85vh] overflow-hidden">
            <DialogHeader>
              <DialogTitle className="text-text-ui">
                {synthesisResult?.type === 'summary' ? 'Unified Summary' : 'Comparative Analysis'}
              </DialogTitle>
              <DialogDescription className="text-muted-ui">
                AI-generated synthesis from {synthesisResult?.sources.length || 0} documents with source attribution
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {/* Markdown preview */}
              <div className="max-h-[50vh] overflow-y-auto p-4 bg-black-ui border border-border-ui rounded-lg">
                <pre className="whitespace-pre-wrap text-sm text-text-ui font-mono">
                  {synthesisResult?.markdown}
                </pre>
              </div>

              {/* Sources section */}
              {synthesisResult && synthesisResult.sources.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-text-ui mb-2">Sources</h3>
                  <div className="space-y-2">
                    {synthesisResult.sources.map((source) => (
                      <Card key={source.document_id} className="bg-black-ui/30 border-border-ui">
                        <CardContent className="p-3">
                          <p className="text-sm font-semibold text-text-ui mb-1">{source.filename}</p>
                          <ul className="list-disc list-inside space-y-1">
                            {source.key_points.map((point, idx) => (
                              <li key={idx} className="text-xs text-muted-ui">{point}</li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="default" size="sm" onClick={handleDownloadSynthesis}>
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
              <Button variant="outline" size="sm" onClick={() => setSynthesisDialogOpen(false)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Loading Dialog */}
        <LoadingDialog open={loadingDialogOpen} message={loadingMessage} />
      </main>
    </ProtectedRoute>
  );
}
