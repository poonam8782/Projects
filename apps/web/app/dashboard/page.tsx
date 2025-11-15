"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import FileUploader from "@/components/FileUploader";
import Link from "next/link";
import type { DocumentMetadata } from '@/lib/types/document';
import {
  getDocuments,
  getDownloadUrl,
  embedDocument,
  generateNotes,
  generateMindmap,
  generateFlashcards,
  exportDocument,
  deleteDocument,
  DocumentUploadResponse,
} from '@/services/api';

export default function Dashboard(): JSX.Element {
  const { user, signOut } = useAuth();
  const router = useRouter();
  
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(true);
  const [exportFormat, setExportFormat] = useState<'markdown' | 'pdf'>('markdown');

  // Fetch documents from backend
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        setLoadingDocs(true);
        const docs = await getDocuments();
        if (!mounted) return;
        setDocuments(docs || []);
      } catch (err: any) {
        console.error('Failed to load documents', err);
      } finally {
        if (mounted) setLoadingDocs(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const refreshDocuments = async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs || []);
    } catch (err: any) {
      console.error('Failed to refresh documents', err);
    }
  };

  const handleUploadComplete = (result: DocumentUploadResponse) => {
    console.log('Upload complete:', result);
    refreshDocuments();
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSelectAll = () => setSelected(new Set(documents.map((d) => d.id)));
  const handleClear = () => setSelected(new Set());

  const handleExport = async () => {
    if (selected.size === 0) {
      window.alert("Please select at least one document to export.");
      return;
    }

    try {
      for (const id of Array.from(selected)) {
        const resp = await exportDocument({ 
          document_id: id, 
          format: exportFormat, 
          include_notes: true, 
          include_flashcards: true, 
          include_chat_history: false 
        });
        if (resp?.download_url) {
          window.open(resp.download_url, '_blank');
        }
      }
    } catch (err: any) {
      console.error('Export error', err);
      window.alert('Export failed: ' + (err?.message || String(err)));
    } finally {
      setSelected(new Set());
    }
  };

  const handleDownload = async (documentId: string) => {
    try {
      const url = await getDownloadUrl(documentId);
      if (url) window.open(url, '_blank');
    } catch (err: any) {
      console.error('Download error', err);
      window.alert('Failed to get download URL: ' + (err?.message || String(err)));
    }
  };

  const handleEmbed = async (documentId: string) => {
    try {
      await embedDocument(documentId);
      window.alert('Embedding started/queued for document');
      setDocuments((prev) => prev.map(d => d.id === documentId ? { ...d, status: 'embedded' } : d));
    } catch (err: any) {
      console.error('Embed error', err);
      window.alert('Failed to embed: ' + (err?.message || String(err)));
    }
  };

  const handleGenerateNotes = async (documentId: string) => {
    try {
      const res = await generateNotes(documentId);
      if (res?.download_url) window.open(res.download_url, '_blank');
      else window.alert('Notes generation requested.');
    } catch (err: any) {
      console.error('Notes error', err);
      window.alert('Failed to generate notes: ' + (err?.message || String(err)));
    }
  };

  const handleGenerateMindmap = async (documentId: string) => {
    try {
      const res = await generateMindmap(documentId, 'svg');
      if (res?.download_url) window.open(res.download_url, '_blank');
      else window.alert('Mindmap generation requested.');
    } catch (err: any) {
      console.error('Mindmap error', err);
      window.alert('Failed to generate mindmap: ' + (err?.message || String(err)));
    }
  };

  const handleGenerateFlashcards = async (documentId: string) => {
    try {
      const res = await generateFlashcards(documentId, 10);
      window.alert(`Flashcards generation status: ${res?.status || 'requested'}`);
    } catch (err: any) {
      console.error('Flashcards error', err);
      window.alert('Failed to generate flashcards: ' + (err?.message || String(err)));
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!window.confirm('Delete this document and all associated data?')) return;
    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(documentId);
        return next;
      });
    } catch (err: any) {
      console.error('Delete error', err);
      window.alert('Failed to delete document: ' + (err?.message || String(err)));
    }
  };

  const handleSignOut = async () => {
    await signOut();
    router.push('/login');
  };

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <main className="font-body bg-neo-bg min-h-screen">
      <style jsx global>{`
        body { 
          background-color: #FFFAE5 !important; 
          color: #0f0f0f; 
        }
        ::selection { 
          background-color: #0f0f0f; 
          color: #A3FF00; 
        }
        ::-webkit-scrollbar { 
          width: 16px; 
        }
        ::-webkit-scrollbar-track { 
          background: #FFFAE5; 
          border-left: 3px solid #0f0f0f; 
        }
        ::-webkit-scrollbar-thumb { 
          background: #0f0f0f; 
          border: 3px solid #FFFAE5; 
        }
        ::-webkit-scrollbar-thumb:hover { 
          background: #FF4D00; 
        }
      `}</style>

      <nav className="sticky top-0 left-0 w-full flex justify-between items-center p-4 md:p-6 z-50 bg-neo-black text-neo-bg border-b-4 border-neo-accent shadow-neo">
        <div className="flex items-center gap-12">
          <Link href="/" className="font-heavy text-3xl tracking-tighter hover:text-neo-accent transition-colors">
            NEURA.
          </Link>
          <div className="pointer-events-auto hidden md:flex gap-8 font-bold text-lg items-center">
            <Link href="/features" className="hover:text-neo-main transition-colors">Features</Link>
            <Link href="/benefits" className="hover:text-neo-main transition-colors">Benefits</Link>
            <Link href="/pricing" className="hover:text-neo-main transition-colors">Pricing</Link>
            <Link href="/contact" className="hover:text-neo-main transition-colors">Contact</Link>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <Link href="/pricing" className="border-2 border-neo-accent bg-neo-accent text-neo-black px-6 py-2 font-heavy hover:bg-neo-black hover:text-neo-accent transition-all duration-300">
            Upgrade
          </Link>
          <button onClick={handleSignOut} className="font-body font-bold hover:text-neo-main transition-colors">
            Sign Out
          </button>
        </div>
      </nav>

      <div className="container mx-auto p-4 md:p-12 space-y-12">
        <div>
          <h1 className="font-heavy text-5xl md:text-7xl text-black">Dashboard</h1>
          <p className="font-mono text-lg text-gray-700 mt-2">
            Signed in as: {user?.email || "Loading..."}
          </p>
        </div>

        <section className="bg-neo-white border-4 border-black shadow-neo p-8">
          <h2 className="font-heavy text-3xl uppercase text-black mb-6 border-b-2 border-black/20 pb-4">
            Upload Document
          </h2>
          <FileUploader onUploadComplete={handleUploadComplete} className="border-0 bg-transparent p-0" />
        </section>

        <section>
          <h2 className="font-heavy text-3xl uppercase text-black mb-6">Your Documents</h2>

          <div className="flex flex-col md:flex-row justify-between items-center mb-6 bg-neo-white border-4 border-black shadow-neo-sm p-4">
            <div className="flex items-center gap-4">
              <button className="font-heavy text-sm text-black hover:text-neo-main">
                {selected.size} selected
              </button>
              <button onClick={handleSelectAll} className="font-heavy text-sm text-neo-blue hover:text-neo-main">
                Select All
              </button>
              <button onClick={handleClear} className="font-heavy text-sm text-neo-blue hover:text-neo-main">
                Clear
              </button>
            </div>
            <div className="flex items-center gap-2 mt-4 md:mt-0">
              <span className="font-mono text-sm">Export as:</span>
              <button 
                onClick={() => setExportFormat('markdown')} 
                className={`border-2 border-black text-black font-heavy text-xs px-3 py-1 transition-all ${
                  exportFormat === 'markdown' ? 'bg-neo-black text-neo-white' : 'bg-neo-white hover:bg-neo-black hover:text-neo-white'
                }`}
              >
                MARKDOWN
              </button>
              <button 
                onClick={() => setExportFormat('pdf')} 
                className={`border-2 border-black text-black font-heavy text-xs px-3 py-1 transition-all ${
                  exportFormat === 'pdf' ? 'bg-neo-black text-neo-white' : 'bg-neo-white hover:bg-neo-black hover:text-neo-white'
                }`}
              >
                PDF
              </button>
              <button 
                onClick={handleExport} 
                className="border-4 border-neo-blue bg-neo-blue text-white font-heavy text-sm px-6 py-2 hover:bg-neo-white hover:text-neo-blue transition-all"
              >
                Export
              </button>
            </div>
          </div>

          <div className="space-y-6">
            {loadingDocs && (
              <div className="p-6 font-mono text-center">Loading documents...</div>
            )}
            
            {!loadingDocs && documents.length === 0 && (
              <div className="p-6 font-mono text-center">
                No documents found. Upload one to get started.
              </div>
            )}
            
            {documents.map((doc) => {
              const humanSize = typeof doc.size_bytes === 'number' ? formatBytes(doc.size_bytes) : '-';
              const uploaded = doc.created_at ? new Date(doc.created_at).toLocaleString() : '-';
              const type = doc.mime_type || doc.filename.split('.').pop() || '';
              
              return (
                <div 
                  key={doc.id} 
                  className="doc-item bg-neo-white border-4 border-black shadow-neo flex flex-col hover:-translate-y-1 transition-transform duration-200"
                >
                  <div className="p-6">
                    <div className="flex justify-between items-start">
                      <div className="flex items-center gap-3 min-w-0">
                        <input
                          type="checkbox"
                          checked={selected.has(doc.id)}
                          onChange={() => toggleSelect(doc.id)}
                          className="w-4 h-4"
                          aria-label={`Select ${doc.filename}`}
                        />
                        <h3 className="font-heavy text-2xl text-black truncate">{doc.filename}</h3>
                      </div>
                      <span className="font-mono text-xs uppercase bg-neo-accent text-black border-2 border-black px-2 py-1">
                        {doc.status?.toUpperCase() || 'READY'}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 mt-4 font-mono text-sm">
                      <div>
                        <p className="text-gray-600 uppercase">Size</p>
                        <p className="font-bold text-black">{humanSize}</p>
                      </div>
                      <div>
                        <p className="text-gray-600 uppercase">Uploaded</p>
                        <p className="font-bold text-black">{uploaded}</p>
                      </div>
                      <div>
                        <p className="text-gray-600 uppercase">Type</p>
                        <p className="font-bold text-black">{type}</p>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-end gap-2 border-t-4 border-black p-3 bg-neo-bg/50">
                    <button 
                      onClick={() => handleEmbed(doc.id)} 
                      className="p-2 text-black hover:text-neo-purple transition-colors" 
                      title="Generate Embedding"
                    >
                      ✨
                    </button>
                    <button 
                      onClick={() => handleGenerateNotes(doc.id)} 
                      className="p-2 text-black hover:text-neo-blue transition-colors" 
                      title="Generate Study Notes"
                    >
                      📄
                    </button>
                    <button 
                      onClick={() => handleGenerateMindmap(doc.id)} 
                      className="p-2 text-black hover:text-neo-blue transition-colors" 
                      title="Generate Mind Map"
                    >
                      🕸️
                    </button>
                    <button 
                      onClick={() => handleGenerateFlashcards(doc.id)} 
                      className="p-2 text-black hover:text-neo-blue transition-colors" 
                      title="Generate Flashcard"
                    >
                      🎓
                    </button>
                    <button 
                      onClick={() => window.open(`/document/${doc.id}`, '_blank')} 
                      className="p-2 text-black hover:text-neo-accent transition-colors" 
                      title="View Document"
                    >
                      👁️
                    </button>
                    <button 
                      onClick={() => handleDownload(doc.id)} 
                      className="p-2 text-black hover:text-neo-blue transition-colors" 
                      title="Download Document"
                    >
                      ⬇️
                    </button>
                    <button 
                      onClick={() => handleDelete(doc.id)} 
                      className="p-2 text-black hover:text-neo-main transition-colors" 
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}
