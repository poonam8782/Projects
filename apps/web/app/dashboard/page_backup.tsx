"use client";

import React, { useEffect } from "react";

export default function Dashboard(): JSX.Element {
    const loadScript = (src: string, attrs: Record<string, string> = {}) =>
      new Promise<void>((resolve, reject) => {
        if (document.querySelector(`script[src="${src}"]`)) {
          resolve();
          return;
        }
        const s = document.createElement("script");
        s.src = src;
        s.async = true;
        Object.entries(attrs).forEach(([k, v]) => s.setAttribute(k, v));
        s.addEventListener("load", () => resolve());
        s.addEventListener("error", () => reject(new Error("Failed to load " + src)));
        document.body.appendChild(s);
        createdElements.push(s);
      });

  return (
    <ProtectedRoute>
      <TopNav />
      <main
        className="min-h-screen p-8 bg-neo-bg text-neo-black">
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
            <h2 className="text-2xl font-semibold text-text-ui mb-4">
              Upload Document
            </h2>
            <FileUploader onUploadComplete={handleUploadComplete} />
          </div>

          <div>
            <h2 className="text-2xl font-semibold text-text-ui mb-4">
              Your Documents
            </h2>

            {/* Export controls - only show when documents exist */}
            {documents.length > 0 && (
              <div className="flex items-center justify-between mb-4 p-4 bg-neo-white border-2 border-neo-black rounded-lg">
                <div className="flex items-center gap-4">
                  <span className="text-sm text-muted-ui">
                    {selectedDocuments.size} selected
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleSelectAll}
                    disabled={selectedDocuments.size === documents.length}>
                    Select All
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDeselectAll}
                    disabled={selectedDocuments.size === 0}>
                    Clear
                  </Button>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Button
                      variant={
                        exportFormat === "markdown" ? "default" : "outline"
                      }
                      size="sm"
                      onClick={() => setExportFormat("markdown")}>
                      Markdown
                    </Button>
                    <Button
                      variant={exportFormat === "pdf" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setExportFormat("pdf")}>
                      PDF
                    </Button>
                  </div>
                  <Button
                    onClick={() => void handleExport()}
                    disabled={selectedDocuments.size === 0 || exporting}>
                    {exporting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        {selectedDocuments.size === 1
                          ? "Exporting..."
                          : "Synthesizing..."}
                      </>
                    ) : (
                      <>
                        <FileArchive className="w-4 h-4 mr-2" />
                        {selectedDocuments.size === 1
                          ? "Export"
                          : selectedDocuments.size > 1
                          ? "Synthesize"
                          : "Export"}
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Loading state */}
            {loading && (
              <Card className="bg-neo-white border-2 border-neo-black">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-neo-main animate-spin mb-4" />
                  <p className="text-neo-black/70">Loading documents...</p>
                </CardContent>
              </Card>
            )}

            {/* Error state */}
            {error && !loading && (
              <Card className="bg-neo-white border-2 border-neo-black">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <AlertCircle className="w-8 h-8 text-neo-main mb-4" />
                  <p className="text-neo-black/70 mb-4">{error}</p>
                  <Button
                    variant="outline"
                    onClick={() => void fetchDocuments()}>
                    Retry
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Empty state */}
            {!loading && !error && documents.length === 0 && (
              <Card className="bg-neo-white border-2 border-neo-black">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <FileText className="w-12 h-12 text-neo-main mb-4" />
                  <p className="text-neo-black/70">
                    No documents yet. Upload your first document above.
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Document grid */}
            {!loading && !error && documents.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {documents.map((document) => (
                  <Card
                    key={document.id}
                    className="bg-neo-white border-2 border-neo-black hover:border-neo-main transition-colors">
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-2 flex-1 min-w-0">
                          <Checkbox
                            checked={selectedDocuments.has(document.id)}
                            onCheckedChange={() =>
                              handleToggleSelect(document.id)
                            }
                            aria-label={`Select ${document.filename}`}
                            className="flex-shrink-0"
                          />
                          <FileText className="w-5 h-5 text-text-ui flex-shrink-0" />
                          <button
                            onClick={() => handleOpen(document)}
                            className="text-sm truncate text-left hover:underline focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded"
                            tabIndex={0}>
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
                        <span className="text-text-ui">
                          {formatFileSize(document.size_bytes)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-ui">Uploaded:</span>
                        <span className="text-text-ui">
                          {formatDate(document.created_at)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-ui">Type:</span>
                        <Badge variant="outline" className="text-xs">
                          {getFileTypeLabel(document.mime_type)}
                        </Badge>
                      </div>
                      {flashcardMetadata.has(document.id) &&
                        flashcardMetadata.get(document.id)!.count > 0 && (
                          <>
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-muted-ui">Flashcards:</span>
                              <span className="text-text-ui">
                                {flashcardMetadata.get(document.id)!.count}{" "}
                                flashcards
                              </span>
                            </div>
                            {(() => {
                              const metadata = flashcardMetadata.get(
                                document.id,
                              );
                              const nextReview = metadata?.nextReview;
                              if (nextReview) {
                                return (
                                  <div className="flex items-center justify-between text-sm">
                                    <span className="text-muted-ui">
                                      Next review:
                                    </span>
                                    <span className="text-text-ui">
                                      {nextReview <= new Date().toISOString()
                                        ? "Due now"
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
                      {(document.status === "extracted" ||
                        document.status === "embedded" ||
                        document.status === "failed") && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEmbed(document)}
                          disabled={
                            embeddingDocuments.has(document.id) ||
                            document.status === "embedded"
                          }
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Generate embeddings for AI chat"
                          title="Generate embeddings for AI chat">
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
                          title="View generated notes">
                          <BookOpen className="w-4 h-4" />
                        </Button>
                      )}
                      {(document.status === "extracted" ||
                        document.status === "embedded" ||
                        document.status === "failed") && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleGenerateNotes(document)}
                          disabled={generatingNotes.has(document.id)}
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Generate notes"
                          title="Generate study notes">
                          {generatingNotes.has(document.id) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <FileDown className="w-4 h-4" />
                          )}
                        </Button>
                      )}
                      {(document.status === "extracted" ||
                        document.status === "embedded" ||
                        document.status === "failed") && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleGenerateMindmap(document)}
                          disabled={generatingMindmaps.has(document.id)}
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Generate mindmap"
                          title="Generate mindmap">
                          {generatingMindmaps.has(document.id) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Network className="w-4 h-4" />
                          )}
                        </Button>
                      )}
                      {flashcardMetadata.has(document.id) &&
                        flashcardMetadata.get(document.id)!.count > 0 && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewFlashcards(document)}
                            className="text-primary hover:text-primary/80"
                            aria-label="View flashcards"
                            title="View flashcard library">
                            <GraduationCap className="w-4 h-4" />
                          </Button>
                        )}
                      {(document.status === "extracted" ||
                        document.status === "embedded" ||
                        document.status === "failed") && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleGenerateFlashcards(document)}
                          disabled={generatingFlashcards.has(document.id)}
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Generate flashcards"
                          title="Generate flashcards">
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
                        title="View document">
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(document)}
                        className="text-text-ui hover:text-text-ui"
                        aria-label="Download document"
                        title="Download document">
                        <Download className="w-4 h-4" />
                      </Button>
                      {document.status === "embedded" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleChat(document)}
                          className="text-text-ui hover:text-text-ui"
                          aria-label="Chat with document"
                          title="Chat with document">
                          <MessageSquare className="w-4 h-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(document)}
                        className="text-muted-ui hover:text-text-ui"
                        aria-label="Delete document"
                        title="Delete document">
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
          <DialogContent className="bg-neo-white border-4 border-neo-black">
            <DialogHeader>
              <DialogTitle>Delete Document</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete{" "}
                <strong>{documentToDelete?.filename}</strong>? This action
                cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
                disabled={deleting}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => void confirmDelete()}
                disabled={deleting}>
                {deleting ? "Deleting..." : "Delete"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Notes preview dialog */}
        <Dialog open={notesDialogOpen} onOpenChange={setNotesDialogOpen}>
          <DialogContent className="bg-neo-white border-4 border-neo-black max-w-3xl">
            <DialogHeader>
              <DialogTitle className="text-2xl text-neo-black">
                📝 Study Notes Generated!
              </DialogTitle>
              <DialogDescription className="text-neo-black/70">
                AI-generated study notes from your document
              </DialogDescription>
            </DialogHeader>
            {currentNotes && (
              <div className="py-4 space-y-4">
                {/* Notes preview */}
                <div className="max-h-[50vh] overflow-y-auto p-4 bg-neo-bg border-2 border-neo-black rounded-lg">
                  <pre className="whitespace-pre-wrap text-sm text-neo-black font-mono leading-relaxed">
                    {currentNotes.content}
                  </pre>
                </div>

                {/* Info */}
                <div className="flex items-center justify-center gap-2 text-sm text-neo-black/60">
                  <span>📄 {currentNotes.filename}</span>
                </div>
              </div>
            )}
            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button
                variant="outline"
                size="lg"
                onClick={() => setNotesDialogOpen(false)}
                className="w-full sm:w-auto">
                Close
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={() =>
                  currentNotes?.downloadUrl &&
                  window.open(currentNotes.downloadUrl, "_blank")
                }
                disabled={!currentNotes}
                className="w-full sm:w-auto">
                📥 Download Markdown
              </Button>
              <Button
                variant="default"
                size="lg"
                onClick={() => {
                  // Extract document ID from the notes context
                  const docId = documents.find(
                    (d) =>
                      currentNotes?.filename.includes(d.id) ||
                      currentNotes?.filename.includes(
                        d.filename.replace(/\.[^/.]+$/, ""),
                      ),
                  )?.id;
                  if (docId) {
                    setNotesDialogOpen(false);
                    router.push(`/notes/${docId}`);
                  }
                }}
                disabled={!currentNotes}
                className="w-full sm:w-auto bg-primary hover:bg-primary/90">
                � View Full Notes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Mindmap viewer dialog */}
        <Dialog open={mindmapDialogOpen} onOpenChange={setMindmapDialogOpen}>
          <DialogContent className="bg-neo-white border-4 border-neo-black max-w-6xl max-h-[90vh] overflow-hidden">
            <DialogHeader>
              <DialogTitle className="text-neo-black">
                {currentMindmap?.filename || "Generated Mindmap"}
              </DialogTitle>
              <DialogDescription className="text-neo-black/70">
                Interactive mindmap visualization of your document structure.
              </DialogDescription>
            </DialogHeader>
            {currentMindmap && (
              <div className="mb-4 bg-neo-white">
                <MindmapViewerUnified
                  downloadUrl={currentMindmap.downloadUrl}
                  documentName={currentMindmap.filename}
                  format={currentMindmap.format}
                  showControls
                  allowFullscreen
                  className="h-[600px] bg-neo-white"
                />
              </div>
            )}
            <DialogFooter>
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  currentMindmap?.downloadUrl &&
                  window.open(currentMindmap.downloadUrl, "_blank")
                }
                disabled={!currentMindmap}>
                Download {currentMindmap?.format?.toUpperCase() || "Mindmap"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setMindmapDialogOpen(false)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Flashcards preview dialog */}
        <Dialog
          open={flashcardsDialogOpen}
          onOpenChange={setFlashcardsDialogOpen}>
          <DialogContent className="bg-neo-white border-4 border-neo-black max-w-xl">
            <DialogHeader>
              <DialogTitle className="text-2xl text-neo-black">
                ✨ Flashcards Generated!
              </DialogTitle>
              <DialogDescription className="text-neo-black/70">
                {currentFlashcards?.count ? (
                  <>
                    Successfully generated {currentFlashcards.count} flashcard
                    {currentFlashcards.count !== 1 ? "s" : ""} from your
                    document
                  </>
                ) : (
                  "Your flashcards are ready"
                )}
              </DialogDescription>
            </DialogHeader>
            {currentFlashcards && currentFlashcards.flashcards.length > 0 && (
              <div className="py-6 space-y-4">
                {/* Sample flashcard preview */}
                <div className="bg-neo-bg border-2 border-neo-black rounded-lg p-4">
                  <p className="text-xs text-neo-black/60 mb-2">
                    Sample flashcard:
                  </p>
                  <p className="text-sm font-medium text-neo-black mb-2">
                    Q: {currentFlashcards.flashcards[0]?.question}
                  </p>
                  <p className="text-sm text-neo-black/70">
                    A:{" "}
                    {currentFlashcards.flashcards[0]?.answer?.substring(0, 100)}
                    {(currentFlashcards.flashcards[0]?.answer?.length || 0) >
                    100
                      ? "..."
                      : ""}
                  </p>
                </div>

                {/* Stats */}
                <div className="flex items-center justify-center gap-8 text-center py-4">
                  <div>
                    <p className="text-3xl font-bold text-neo-black">
                      {currentFlashcards.count}
                    </p>
                    <p className="text-xs text-neo-black/60 mt-1">
                      Total Cards
                    </p>
                  </div>
                  <div className="h-12 w-px bg-neo-black/20" />
                  <div>
                    <p className="text-3xl font-bold text-gray-900 dark:text-text-ui">
                      {currentFlashcards.count}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-muted-ui mt-1">
                      Ready to Review
                    </p>
                  </div>
                </div>
              </div>
            )}
            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button
                variant="outline"
                size="lg"
                onClick={() => setFlashcardsDialogOpen(false)}
                className="w-full sm:w-auto">
                Close
              </Button>
              <Button
                variant="default"
                size="lg"
                onClick={() => {
                  setFlashcardsDialogOpen(false);
                  router.push(`/flashcards/${currentFlashcards?.documentId}`);
                }}
                disabled={
                  !currentFlashcards ||
                  currentFlashcards.flashcards.length === 0
                }
                className="w-full sm:w-auto bg-primary hover:bg-primary/90">
                <GraduationCap className="w-5 h-5 mr-2" />
                Start Practice Session
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Synthesis result dialog */}
        <Dialog
          open={synthesisDialogOpen}
          onOpenChange={setSynthesisDialogOpen}>
          <DialogContent className="bg-neo-white border-4 border-neo-black max-w-4xl max-h-[85vh] overflow-hidden">
            <DialogHeader>
              <DialogTitle className="text-neo-black">
                {synthesisResult?.type === "summary"
                  ? "Unified Summary"
                  : "Comparative Analysis"}
              </DialogTitle>
              <DialogDescription className="text-neo-black/70">
                AI-generated synthesis from{" "}
                {synthesisResult?.sources.length || 0} documents with source
                attribution
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {/* Markdown preview */}
              <div className="max-h-[50vh] overflow-y-auto p-4 bg-neo-bg border-2 border-neo-black rounded-lg">
                <pre className="whitespace-pre-wrap text-sm text-neo-black font-mono">
                  {synthesisResult?.markdown}
                </pre>
              </div>

              {/* Sources section */}
              {synthesisResult && synthesisResult.sources.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-neo-black mb-2">
                    Sources
                  </h3>
                  <div className="space-y-2">
                    {synthesisResult.sources.map((source) => (
                      <Card
                        key={source.document_id}
                        className="bg-neo-bg border-2 border-neo-black">
                        <CardContent className="p-3">
                          <p className="text-sm font-semibold text-neo-black mb-1">
                            {source.filename}
                          </p>
                          <ul className="list-disc list-inside space-y-1">
                            {source.key_points.map((point, idx) => (
                              <li key={idx} className="text-xs text-neo-black/70">
                                {point}
                              </li>
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
              <Button
                variant="default"
                size="sm"
                onClick={handleDownloadSynthesis}>
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSynthesisDialogOpen(false)}>
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
