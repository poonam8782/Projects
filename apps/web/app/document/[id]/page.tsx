"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ProtectedRoute } from "@/lib/auth/protected-route";
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
} from "@neura/ui";
import DocumentChat from "@/components/DocumentChat";
import { getDocument } from "@/services/api";
import type { DocumentMetadata } from "@/lib/types/document";
import { formatFileSize, formatDate } from "@/lib/utils/format";
import { ArrowLeft, FileText, Loader2, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { getFileTypeLabel, getStatusBadgeVariant } from "@/lib/utils/document";

export default function DocumentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const documentId = params?.id as string;

  const [document, setDocument] = useState<DocumentMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocument = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const doc = await getDocument(documentId);
      setDocument(doc);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch document";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    if (documentId) {
      void fetchDocument();
    }
  }, [documentId, fetchDocument]);

  const handleBackToDashboard = () => router.push("/dashboard");

  return (
    <ProtectedRoute>
      <main className="min-h-screen p-8 bg-black-ui text-text-ui">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <Button variant="ghost" onClick={handleBackToDashboard} aria-label="Navigate back to dashboard">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
          </Button>
        </div>

        {/* Loading */}
        {loading && (
          <Card className="bg-surface-ui border-border-ui">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-muted-ui animate-spin mb-4" />
              <p className="text-muted-ui">Loading document...</p>
            </CardContent>
          </Card>
        )}

        {/* Error */}
        {error && !loading && (
          <Card className="bg-surface-ui border-border-ui">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <AlertCircle className="w-8 h-8 text-muted-ui mb-4" />
              <p className="text-muted-ui mb-4">{error}</p>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => void fetchDocument()}>Retry</Button>
                <Button variant="outline" onClick={handleBackToDashboard}>Back to Dashboard</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Content */}
        {!loading && !error && document && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left: metadata */}
            <section className="lg:col-span-1">
              <Card className="bg-surface-ui border-border-ui">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="w-5 h-5" />
                      <CardTitle className="truncate max-w-[22rem]" title={document.filename}>{document.filename}</CardTitle>
                    </div>
                    <Badge variant={getStatusBadgeVariant(document.status)}>{document.status}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex items-center justify-between"><span className="text-muted-ui">Type</span><span className="text-text-ui">{getFileTypeLabel(document.mime_type)}</span></div>
                  <div className="flex items-center justify-between"><span className="text-muted-ui">Size</span><span className="text-text-ui">{formatFileSize(document.size_bytes)}</span></div>
                  <div className="flex items-center justify-between"><span className="text-muted-ui">Uploaded</span><span className="text-text-ui">{formatDate(document.created_at)}</span></div>
                  <div className="flex items-center justify-between"><span className="text-muted-ui">Updated</span><span className="text-text-ui">{formatDate(document.updated_at)}</span></div>
                  <div className="text-muted-ui text-xs break-all"><span className="font-semibold text-text-ui">ID:</span> {document.id}</div>
                </CardContent>
              </Card>
            </section>

            {/* Right: chat */}
            <section className="lg:col-span-2">
              {document.status === "embedded" ? (
                <DocumentChat documentId={documentId} documentName={document.filename} />
              ) : (
                <Card className="bg-surface-ui border-border-ui">
                  <CardContent className="py-8 text-center text-muted-ui">
                    This document must be embedded before you can chat with it.
                    <div className="mt-4">
                      <Button variant="outline" onClick={handleBackToDashboard}>Back to Dashboard</Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </section>
          </div>
        )}
      </main>
    </ProtectedRoute>
  );
}
