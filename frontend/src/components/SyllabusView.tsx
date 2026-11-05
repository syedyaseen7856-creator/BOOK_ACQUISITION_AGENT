'use client';

import React, { useState, useRef, useMemo } from 'react';
import {
  Upload,
  FileText,
  Sparkles,
  AlertTriangle,
  Plus,
  Trash2,
  Edit2,
  X,
  ArrowRight,
  RefreshCw,
  GraduationCap,
  CheckCircle2,
  Building2,
  Layers,
  BookOpen,
  Zap,
  BookMarked,
  Calendar,
  Award,
} from 'lucide-react';
import {
  SyllabusUploadResponse,
  ExtractedBookRecord,
  BookType,
} from '@/types/book';
import {
  uploadSyllabusFile,
  updateSyllabusBooks,
  addSyllabusBook,
  deleteSyllabusBook,
  startBatchSearch,
} from '@/lib/api';

interface SyllabusViewProps {
  onStartBatch: (batchId: string) => void;
}

export const SyllabusView: React.FC<SyllabusViewProps> = ({ onStartBatch }) => {
  const [syllabus, setSyllabus] = useState<SyllabusUploadResponse | null>(null);
  const [books, setBooks] = useState<ExtractedBookRecord[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<'ALL' | 'TEXTBOOK' | 'REFERENCE'>('ALL');

  const [editingBookId, setEditingBookId] = useState<string | null>(null);
  const [editFormData, setEditFormData] = useState<Partial<ExtractedBookRecord>>({});
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newBookData, setNewBookData] = useState<Partial<ExtractedBookRecord>>({
    title: '',
    author: '',
    book_type: 'TEXTBOOK',
    subject: '',
    year: 2024,
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const resp = await uploadSyllabusFile(file);
      setSyllabus(resp);
      setBooks(resp.books);
      if (resp.extracted_subjects && resp.extracted_subjects.length > 0) {
        setSelectedSubject(resp.extracted_subjects[0]);
      } else {
        setSelectedSubject(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to process syllabus document.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleLoadDemoSyllabus = async () => {
    const demoText = `Department of Computer Science & Engineering
Anna University of Technology
Degree: B.E. Computer Science and Engineering
Semester: Semester V
Academic Year: 2024-2025

Course: CS301 - Operating Systems
Unit I: Concurrency & Virtual Memory
Textbooks:
1. Silberschatz, A., Galvin, P.B., and Gagne, G., "Operating System Concepts", 10th Edition, Wiley, 2018. ISBN: 978-1119456339.
2. Arpaci-Dusseau, Remzi H., and Arpaci-Dusseau, Andrea C., "Operating Systems: Three Easy Pieces", 1st Edition, Arpaci-Dusseau Books, 2018.

Unit II: Distributed Systems & Case Studies
Reference Books:
3. Andrew S. Tanenbaum and Herbert Bos, "Modern Operating Systems", 4th Edition, Pearson, 2014. ISBN: 978-0133591620.
4. Mary Shelley, Frankenstein; or, The Modern Prometheus, Penguin Classics, 2003.
5. Calculus Volume 1 by Gilbert Strang and Edwin Jed Herman, OpenStax, 2016.

Course: CS302 - Database Management Systems
Unit I: Relational Models & SQL
Textbooks:
1. Abraham Silberschatz, Henry F. Korth, and S. Sudarshan, "Database System Concepts", 7th Edition, McGraw-Hill, 2019. ISBN: 978-0078022159.

Unit II: Query Optimization & Transaction Processing
Reference Books:
2. Raghu Ramakrishnan and Johannes Gehrke, "Database Management Systems", 3rd Edition, McGraw-Hill, 2003.
3. Lewis Carroll, Alice's Adventures in Wonderland, Macmillan, 1865.`;

    const blob = new Blob([demoText], { type: 'text/plain' });
    const file = new File([blob], 'University_CS_Curriculum_Syllabus.txt', { type: 'text/plain' });
    await handleFileUpload(file);
  };

  const toggleSelectBook = (id: string) => {
    setBooks((prev) =>
      prev.map((b) => (b.id === id ? { ...b, is_selected: !b.is_selected } : b))
    );
  };

  const selectAll = (selected: boolean) => {
    setBooks((prev) =>
      prev.map((b) => {
        if (!selectedSubject || b.subject === selectedSubject) {
          return { ...b, is_selected: selected };
        }
        return b;
      })
    );
  };

  const handleStartEdit = (b: ExtractedBookRecord) => {
    setEditingBookId(b.id);
    setEditFormData({ ...b });
  };

  const handleSaveEdit = async () => {
    if (!syllabus || !editingBookId) return;
    const updated = books.map((b) =>
      b.id === editingBookId ? ({ ...b, ...editFormData } as ExtractedBookRecord) : b
    );
    setBooks(updated);
    setEditingBookId(null);
    try {
      await updateSyllabusBooks(syllabus.syllabus_id, updated);
    } catch {
      setError('Failed to persist book update.');
    }
  };

  const handleDeleteBook = async (id: string) => {
    if (!syllabus) return;
    setBooks((prev) => prev.filter((b) => b.id !== id));
    try {
      await deleteSyllabusBook(syllabus.syllabus_id, id);
    } catch {}
  };

  const handleAddNewBook = async () => {
    if (!syllabus || !newBookData.title) return;
    try {
      const added = await addSyllabusBook(syllabus.syllabus_id, {
        ...newBookData,
        subject: newBookData.subject || selectedSubject || 'General Syllabus Reading',
        is_selected: true,
        confidence: 1.0,
      });
      setBooks((prev) => [...prev, added]);
      setIsAddingNew(false);
      setNewBookData({ title: '', author: '', book_type: 'TEXTBOOK', subject: '', year: 2024 });
    } catch {
      setError('Failed to add custom book.');
    }
  };

  // Launch standard batch search on selected books
  const handleLaunchBatchSearch = async () => {
    if (!syllabus) return;
    const selectedIds = books
      .filter((b) => b.is_selected && (!selectedSubject || b.subject === selectedSubject))
      .map((b) => b.id);

    if (selectedIds.length === 0) {
      setError('Please select at least one book to search.');
      return;
    }

    setIsSearching(true);
    setError(null);
    try {
      const batchResp = await startBatchSearch(syllabus.syllabus_id, selectedIds);
      onStartBatch(batchResp.batch_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start batch search.');
      setIsSearching(false);
    }
  };

  // Target: Minimum 3-Book Reference Acquisition for active subject
  const handleAutoAcquireReferences = async () => {
    if (!syllabus) return;

    // Filter reference books in the current subject (or all reference books if no subject selected)
    const targetSubjectBooks = books.filter((b) => !selectedSubject || b.subject === selectedSubject);
    let refBooks = targetSubjectBooks.filter(
      (b) => b.book_type === 'REFERENCE' || b.book_type === 'SUGGESTED_READING'
    );

    // Fallback if no reference books are explicitly tagged
    if (refBooks.length === 0) {
      refBooks = targetSubjectBooks;
    }

    if (refBooks.length === 0) {
      setError('No reference books available in this subject for auto-acquisition.');
      return;
    }

    setIsSearching(true);
    setError(null);

    try {
      const batchResp = await startBatchSearch(
        syllabus.syllabus_id,
        refBooks.map((b) => b.id)
      );
      onStartBatch(batchResp.batch_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to launch reference auto-acquisition.');
      setIsSearching(false);
    }
  };

  // Group books by subject for the Interactive Subject Grid
  const subjectGroups = useMemo(() => {
    const map = new Map<
      string,
      {
        subject_name: string;
        subject_code?: string | null;
        textbooks: ExtractedBookRecord[];
        reference_books: ExtractedBookRecord[];
        total_books: number;
      }
    >();

    // Initialize from syllabus extracted subjects
    if (syllabus?.extracted_subjects) {
      for (const subj of syllabus.extracted_subjects) {
        map.set(subj, {
          subject_name: subj,
          subject_code: null,
          textbooks: [],
          reference_books: [],
          total_books: 0,
        });
      }
    }

    for (const b of books) {
      const subj = b.subject || 'General Syllabus Reading';
      if (!map.has(subj)) {
        map.set(subj, {
          subject_name: subj,
          subject_code: b.subject_code,
          textbooks: [],
          reference_books: [],
          total_books: 0,
        });
      }
      const entry = map.get(subj)!;
      if (b.subject_code && !entry.subject_code) {
        entry.subject_code = b.subject_code;
      }

      if (b.book_type === 'TEXTBOOK') {
        entry.textbooks.push(b);
      } else {
        entry.reference_books.push(b);
      }
      entry.total_books += 1;
    }

    return Array.from(map.values());
  }, [books, syllabus]);

  // Determine currently active books
  const activeBooks = useMemo(() => {
    let list = books;
    if (selectedSubject) {
      list = list.filter((b) => b.subject === selectedSubject);
    }
    if (categoryFilter === 'TEXTBOOK') {
      list = list.filter((b) => b.book_type === 'TEXTBOOK');
    } else if (categoryFilter === 'REFERENCE') {
      list = list.filter((b) => b.book_type === 'REFERENCE' || b.book_type === 'SUGGESTED_READING');
    }
    return list;
  }, [books, selectedSubject, categoryFilter]);

  const activeTextbooks = useMemo(
    () => activeBooks.filter((b) => b.book_type === 'TEXTBOOK'),
    [activeBooks]
  );
  const activeReferenceBooks = useMemo(
    () => activeBooks.filter((b) => b.book_type === 'REFERENCE' || b.book_type === 'SUGGESTED_READING'),
    [activeBooks]
  );

  const selectedCount = activeBooks.filter((b) => b.is_selected).length;

  return (
    <div className="space-y-6 animate-fadeIn max-w-6xl mx-auto">
      {/* Header Banner */}
      <div className="text-center max-w-3xl mx-auto space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
          <GraduationCap className="w-3.5 h-3.5" />
          <span>Autonomous Syllabus Citation Extractor &amp; Book Discovery</span>
        </div>
        <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
          Syllabus-to-Book <span className="text-indigo-600 dark:text-indigo-400">Discovery &amp; Acquisition</span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
          Upload any college or university syllabus. The agent automatically detects courses, subjects,
          prescribed textbooks, and reference books, and auto-acquires verified legal PDF copies.
        </p>
      </div>

      {/* Upload Zone */}
      {!syllabus && (
        <div className="space-y-4">
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-3xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
              isUploading
                ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20 animate-pulse'
                : 'border-slate-300 dark:border-slate-700 hover:border-indigo-500 bg-white dark:bg-slate-900 shadow-sm hover:shadow-md'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
              accept=".pdf,.docx,.doc,.txt,.text,.md"
              className="hidden"
            />
            <div className="flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-sm">
                <Upload className="w-8 h-8" />
              </div>
              <div className="space-y-1">
                <p className="text-base font-bold text-slate-900 dark:text-slate-100">
                  {isUploading
                    ? 'Extracting syllabus reference books...'
                    : 'Drop your syllabus here or click to browse'}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Supports PDF documents, Word documents, or plain text syllabus files (up to 50MB)
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 text-[11px] font-semibold rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                  .PDF
                </span>
                <span className="px-2.5 py-1 text-[11px] font-semibold rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                  .DOCX
                </span>
                <span className="px-2.5 py-1 text-[11px] font-semibold rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                  .TXT
                </span>
              </div>
            </div>
          </div>

          {/* Quick Demo Test Button */}
          <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
              <Sparkles className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
              <span>Want to test immediately with a multi-course academic curriculum?</span>
            </div>
            <button
              onClick={handleLoadDemoSyllabus}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 hover:bg-indigo-100 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 transition-all shadow-xs"
            >
              <span>Load Sample Multi-Subject Syllabus</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
          <p className="flex-1 font-medium">{error}</p>
          <button onClick={() => setError(null)} className="text-rose-600 hover:text-rose-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Extracted Syllabus Interactive Workspace */}
      {syllabus && (
        <div className="space-y-6">
          {/* Academic Institution & Metadata Banner */}
          <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-3 flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                  <Building2 className="w-3.5 h-3.5" />
                  <span>{syllabus.university || 'Academic Institution'}</span>
                </div>
                {syllabus.department && (
                  <span className="px-2.5 py-0.5 text-[11px] font-semibold rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                    {syllabus.department}
                  </span>
                )}
                {syllabus.programme && (
                  <span className="px-2.5 py-0.5 text-[11px] font-semibold rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                    {syllabus.programme}
                  </span>
                )}
                {syllabus.semester && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-semibold rounded-md bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                    <Award className="w-3 h-3" />
                    <span>{syllabus.semester}</span>
                  </span>
                )}
                {syllabus.academic_year && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-semibold rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                    <Calendar className="w-3 h-3" />
                    <span>{syllabus.academic_year}</span>
                  </span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                <div className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300 font-medium">
                  <FileText className="w-4 h-4 text-indigo-500" />
                  <span>{syllabus.filename}</span>
                </div>
                <span>•</span>
                <span className="uppercase font-mono text-[11px]">{syllabus.file_type}</span>
                {syllabus.page_count && (
                  <>
                    <span>•</span>
                    <span>{syllabus.page_count} Pages</span>
                  </>
                )}
                <span>•</span>
                <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                  {books.length} Books Identified Across {subjectGroups.length} Subject(s)
                </span>
              </div>
            </div>

            <button
              onClick={() => {
                setSyllabus(null);
                setBooks([]);
                setSelectedSubject(null);
              }}
              className="px-3.5 py-2 text-xs font-semibold rounded-xl text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-colors shrink-0"
            >
              Upload Different Syllabus
            </button>
          </div>

          {/* Interactive Subject Grid */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-500" />
                <span>Select Course / Subject Area</span>
              </h3>
              <span className="text-[11px] text-slate-400">Click a subject card to isolate its textbooks &amp; references</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {/* "All Subjects" Tab Card */}
              <div
                onClick={() => setSelectedSubject(null)}
                className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                  selectedSubject === null
                    ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-500 shadow-xs ring-2 ring-indigo-500/20'
                    : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-indigo-300'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
                      Complete Curriculum
                    </span>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      All Subjects &amp; Units
                    </h4>
                  </div>
                  <span className="px-2 py-0.5 text-xs font-bold rounded-lg bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300">
                    {books.length}
                  </span>
                </div>
                <div className="mt-3 flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                  <span>Across {subjectGroups.length} courses</span>
                </div>
              </div>

              {/* Subject Cards */}
              {subjectGroups.map((g) => {
                const isSelected = selectedSubject === g.subject_name;
                return (
                  <div
                    key={g.subject_name}
                    onClick={() => setSelectedSubject(g.subject_name)}
                    className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-500 shadow-xs ring-2 ring-indigo-500/20'
                        : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-indigo-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1 min-w-0">
                        {g.subject_code && (
                          <span className="inline-block px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 border border-slate-200 dark:border-slate-700">
                            {g.subject_code}
                          </span>
                        )}
                        <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                          {g.subject_name}
                        </h4>
                      </div>
                      <span className="px-2 py-0.5 text-xs font-bold rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 shrink-0">
                        {g.total_books}
                      </span>
                    </div>

                    <div className="mt-3 flex items-center gap-3 text-[11px]">
                      <span className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 font-semibold">
                        <BookOpen className="w-3 h-3" />
                        <span>{g.textbooks.length} Textbooks</span>
                      </span>
                      <span>•</span>
                      <span className="inline-flex items-center gap-1 text-purple-600 dark:text-purple-400 font-semibold">
                        <BookMarked className="w-3 h-3" />
                        <span>{g.reference_books.length} References</span>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action & Filter Bar */}
          <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setCategoryFilter('ALL')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                  categoryFilter === 'ALL'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                All Citations ({activeBooks.length})
              </button>
              <button
                onClick={() => setCategoryFilter('TEXTBOOK')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                  categoryFilter === 'TEXTBOOK'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                Prescribed Textbooks ({activeTextbooks.length})
              </button>
              <button
                onClick={() => setCategoryFilter('REFERENCE')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                  categoryFilter === 'REFERENCE'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                Reference Books ({activeReferenceBooks.length})
              </button>

              <div className="h-4 w-px bg-slate-200 dark:bg-slate-800 mx-1 hidden sm:block"></div>

              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <button
                  onClick={() => selectAll(true)}
                  className="hover:text-indigo-600 dark:hover:text-indigo-400 underline font-semibold"
                >
                  Select All
                </button>
                <span>•</span>
                <button
                  onClick={() => selectAll(false)}
                  className="hover:text-indigo-600 dark:hover:text-indigo-400 underline font-semibold"
                >
                  Deselect All
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto justify-end">
              <button
                onClick={() => setIsAddingNew(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Citation</span>
              </button>

              {/* Requirement: Target Minimum 3-Book Reference Acquisition Button */}
              <button
                onClick={handleAutoAcquireReferences}
                disabled={isSearching}
                className="flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm shadow-emerald-600/20 disabled:opacity-50 transition-all shrink-0 active:scale-95"
                title="Automatically search and download at least 3 authorized reference books as PDFs"
              >
                {isSearching ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Zap className="w-4 h-4 text-emerald-200" />
                )}
                <span>Auto-Acquire References (Target: 3 PDFs)</span>
              </button>

              <button
                onClick={handleLaunchBatchSearch}
                disabled={isSearching || selectedCount === 0}
                className="flex items-center justify-center gap-2 px-4 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-600/20 disabled:opacity-50 transition-all shrink-0 active:scale-95"
              >
                {isSearching ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Search Selected ({selectedCount})</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Add Manual Citation Form */}
          {isAddingNew && (
            <div className="p-5 rounded-2xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800/80 space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider">
                  Add Custom Reference Citation
                </h4>
                <button
                  onClick={() => setIsAddingNew(false)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                <input
                  type="text"
                  placeholder="Book Title *"
                  value={newBookData.title || ''}
                  onChange={(e) => setNewBookData({ ...newBookData, title: e.target.value })}
                  className="px-3 py-2 text-xs rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                />
                <input
                  type="text"
                  placeholder="Author(s)"
                  value={newBookData.author || ''}
                  onChange={(e) => setNewBookData({ ...newBookData, author: e.target.value })}
                  className="px-3 py-2 text-xs rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                />
                <input
                  type="text"
                  placeholder="Subject / Topic"
                  value={newBookData.subject || selectedSubject || ''}
                  onChange={(e) => setNewBookData({ ...newBookData, subject: e.target.value })}
                  className="px-3 py-2 text-xs rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                />
                <input
                  type="text"
                  placeholder="Edition (e.g. 10th ed.)"
                  value={newBookData.edition || ''}
                  onChange={(e) => setNewBookData({ ...newBookData, edition: e.target.value })}
                  className="px-3 py-2 text-xs rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                />
                <input
                  type="number"
                  placeholder="Year"
                  value={newBookData.year || ''}
                  onChange={(e) =>
                    setNewBookData({ ...newBookData, year: Number(e.target.value) || undefined })
                  }
                  className="px-3 py-2 text-xs rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                />
                <select
                  value={newBookData.book_type || 'TEXTBOOK'}
                  onChange={(e) =>
                    setNewBookData({ ...newBookData, book_type: e.target.value as BookType })
                  }
                  className="px-3 py-2 text-xs rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="TEXTBOOK">Prescribed Textbook</option>
                  <option value="REFERENCE">Reference Book</option>
                  <option value="SUGGESTED_READING">Suggested Reading</option>
                </select>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setIsAddingNew(false)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-xl text-slate-500 hover:text-slate-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddNewBook}
                  className="px-4 py-1.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  Save Citation
                </button>
              </div>
            </div>
          )}

          {/* Book Lists: Separating Prescribed Textbooks & Reference Books */}
          <div className="space-y-8">
            {/* Section 1: Prescribed Textbooks */}
            {(categoryFilter === 'ALL' || categoryFilter === 'TEXTBOOK') && activeTextbooks.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-indigo-600"></span>
                    <h4 className="text-sm font-extrabold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-2">
                      <span>Prescribed Textbooks</span>
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300">
                        {activeTextbooks.length}
                      </span>
                    </h4>
                  </div>
                  <span className="text-xs text-slate-400">Core required reading materials</span>
                </div>

                <div className="space-y-3">
                  {activeTextbooks.map((b) => renderBookCard(b))}
                </div>
              </div>
            )}

            {/* Section 2: Reference Books */}
            {(categoryFilter === 'ALL' || categoryFilter === 'REFERENCE') && activeReferenceBooks.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-purple-600"></span>
                    <h4 className="text-sm font-extrabold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-2">
                      <span>Reference Books &amp; Supplementary Reading</span>
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-purple-100 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300">
                        {activeReferenceBooks.length}
                      </span>
                    </h4>
                  </div>
                  <span className="text-xs text-slate-400">Target for 3-book PDF acquisition</span>
                </div>

                <div className="space-y-3">
                  {activeReferenceBooks.map((b) => renderBookCard(b))}
                </div>
              </div>
            )}

            {activeBooks.length === 0 && (
              <div className="p-8 text-center rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 text-xs">
                No citations match the selected subject or category filters.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );

  function renderBookCard(b: ExtractedBookRecord) {
    const isEditing = editingBookId === b.id;

    return (
      <div
        key={b.id}
        className={`p-4 rounded-2xl border transition-all duration-150 ${
          b.is_selected
            ? 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:border-indigo-300 dark:hover:border-indigo-700'
            : 'bg-slate-50 dark:bg-slate-950/60 border-slate-200 dark:border-slate-900 opacity-60'
        }`}
      >
        {isEditing ? (
          /* Inline Edit Form */
          <div className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              <input
                type="text"
                value={editFormData.title || ''}
                onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
                className="px-2.5 py-1.5 text-xs rounded-lg bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100"
                placeholder="Title"
              />
              <input
                type="text"
                value={editFormData.author || ''}
                onChange={(e) => setEditFormData({ ...editFormData, author: e.target.value })}
                className="px-2.5 py-1.5 text-xs rounded-lg bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100"
                placeholder="Author"
              />
              <input
                type="text"
                value={editFormData.edition || ''}
                onChange={(e) => setEditFormData({ ...editFormData, edition: e.target.value })}
                className="px-2.5 py-1.5 text-xs rounded-lg bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100"
                placeholder="Edition"
              />
              <input
                type="text"
                value={editFormData.isbn || ''}
                onChange={(e) => setEditFormData({ ...editFormData, isbn: e.target.value })}
                className="px-2.5 py-1.5 text-xs rounded-lg bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100"
                placeholder="ISBN"
              />
              <input
                type="text"
                value={editFormData.subject || ''}
                onChange={(e) => setEditFormData({ ...editFormData, subject: e.target.value })}
                className="px-2.5 py-1.5 text-xs rounded-lg bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100"
                placeholder="Subject"
              />
              <select
                value={editFormData.book_type || 'TEXTBOOK'}
                onChange={(e) =>
                  setEditFormData({ ...editFormData, book_type: e.target.value as BookType })
                }
                className="px-2.5 py-1.5 text-xs rounded-lg bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100"
              >
                <option value="TEXTBOOK">Prescribed Textbook</option>
                <option value="REFERENCE">Reference Book</option>
                <option value="SUGGESTED_READING">Suggested Reading</option>
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditingBookId(null)}
                className="px-3 py-1 text-xs rounded-lg text-slate-500 hover:text-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-3 py-1 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                Save Changes
              </button>
            </div>
          </div>
        ) : (
          /* Book Display Card */
          <div className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={b.is_selected}
              onChange={() => toggleSelectBook(b.id)}
              className="mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer shrink-0"
            />
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 break-words">
                  {b.title}
                </h4>
                <span
                  className={`px-2 py-0.5 text-[10px] font-bold rounded-md shrink-0 ${
                    b.book_type === 'TEXTBOOK'
                      ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800'
                      : 'bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800'
                  }`}
                >
                  {b.book_type === 'TEXTBOOK' ? 'Core Textbook' : 'Reference'}
                </span>
                {b.subject && (
                  <span className="px-2 py-0.5 text-[10px] font-medium rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 shrink-0">
                    {b.subject}
                  </span>
                )}
                {b.page_number && (
                  <span className="text-[11px] text-slate-400 shrink-0">Page {b.page_number}</span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400 mt-1">
                {b.author && (
                  <span>
                    Author: <strong className="text-slate-700 dark:text-slate-300">{b.author}</strong>
                  </span>
                )}
                {b.edition && <span>{b.edition}</span>}
                {b.publisher && <span>{b.publisher}</span>}
                {b.year && <span>({b.year})</span>}
                {b.isbn && (
                  <span className="font-mono text-[11px] text-slate-500">ISBN: {b.isbn}</span>
                )}
              </div>

              {b.context_snippet && (
                <p className="text-[11px] text-slate-500 italic mt-1.5 break-words border-l-2 border-slate-200 dark:border-slate-800 pl-2">
                  &ldquo;{b.context_snippet}&rdquo;
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={() => handleStartEdit(b)}
                className="p-1.5 text-slate-400 hover:text-indigo-600 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                title="Edit book details"
              >
                <Edit2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => handleDeleteBook(b.id)}
                className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                title="Remove book"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }
};
