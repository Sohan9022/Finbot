// src/pages/UploadInvoiceEditor.jsx
import React, { useState, useEffect } from "react";
import { billsAPI } from "../services/api";
import { ChevronLeftIcon, PlusIcon, TrashIcon } from "@heroicons/react/24/solid";
import { useNavigate } from "react-router-dom";

export default function UploadInvoiceEditor() {
   const navigate = useNavigate();

   const [file, setFile] = useState(null);
   const [parsing, setParsing] = useState(false);
   const [parsed, setParsed] = useState(null);
   const [items, setItems] = useState([]);

   const [merchant, setMerchant] = useState("");
   const [date, setDate] = useState("");

   const [totalOverride, setTotalOverride] = useState(null);
   const [ocrConfidence, setOcrConfidence] = useState(null);

   const [error, setError] = useState(null);
   const [saving, setSaving] = useState(false);
   const [success, setSuccess] = useState(null);

   // -----------------------------------------
   // Compute total safely
   // -----------------------------------------
   const computeTotal = () => {
      return items.reduce((sum, it) => {
         const qty = parseFloat(it.qty) || 0;
         const unit = parseFloat(it.unit_price) || 0;
         return sum + qty * unit;
      }, 0);
   };

   // -----------------------------------------
   // Populate UI when parsed is received
   // -----------------------------------------
   useEffect(() => {
      if (!parsed) return;

      setMerchant(parsed.merchant || "");
      setDate(parsed.date || "");

      const mapped = (parsed.items || []).map((it) => {
         const qty = Number(it.qty || it.quantity || 1);
         const line = Number(it.line_total || 0);
         const unit =
            it.unit_price ||
            (qty > 0 && line ? line / qty : 0);

         return {
            id: it.id || null,
            name: it.name || it.product_name || "",
            qty: qty,
            unit_price: unit,
            raw_line: it.raw_line || null,
         };
      });

      setItems(mapped);
      setOcrConfidence(parsed.ocr_confidence ?? null);

      // ensure raw_text is stored
      setParsed((prev) => ({ ...prev, raw_text: parsed.raw_text || "" }));
   }, [parsed]);

   // -----------------------------------------
   // Upload + PARSE (OCR)
   // -----------------------------------------
   async function handleUpload(e) {
      e.preventDefault();
      setError(null);
      setSuccess(null);

      if (!file) return setError("Please choose a file.");

      setParsing(true);
      try {
         const fd = new FormData();
         fd.append("file", file);

         const res = await billsAPI.parseOnly(fd);
         const d = res?.data?.data || {};

         setParsed(d.parsed || {});
      } catch (err) {
         console.error(err);
         setError(err?.response?.data?.detail || err.message || "OCR failed");
      } finally {
         setParsing(false);
      }
   }

   // -----------------------------------------
   // Update item logic (handles numbers safely)
   // -----------------------------------------
   function updateItem(index, key, value) {
      setItems((prev) => {
         const next = [...prev];
         const row = { ...next[index] };

         if (key === "name") {
            row[key] = value;
         } else {
            if (value === "") {
               row[key] = "";
            } else {
               const num = Number(value);
               row[key] = isNaN(num) ? 0 : num;
            }
         }

         next[index] = row;
         return next;
      });
   }

   function addRow() {
      setItems((prev) => [...prev, { id: null, name: "", qty: 1, unit_price: 0, raw_line: null }]);
   }

   function removeRow(index) {
      setItems((prev) => prev.filter((_, i) => i !== index));
   }

   // -----------------------------------------
   // SAVE FINAL BILL
   // -----------------------------------------
   async function handleSave() {
      setSaving(true);
      setError(null);
      setSuccess(null);

      try {
         const payload = {
            merchant: merchant || "Unknown",
            date: date || null,
            total: totalOverride !== null ? Number(totalOverride) : computeTotal(),

            items: items.map((it) => ({
               id: it.id || null,
               product_name: it.name,
               qty: Number(it.qty) || 0,
               unit_price: Number(it.unit_price) || 0,
               line_total: (Number(it.qty) || 0) * (Number(it.unit_price) || 0),
               raw_line: it.raw_line || null,
            })),

            raw_text: parsed?.raw_text || "",
         };

         const res = await billsAPI.saveEdited(payload);

         setSuccess({
            bill_id: res?.data?.data?.bill_id || res?.data?.data?.billId || null,
         });
      } catch (err) {
         console.error(err);
         setError(err?.response?.data?.detail || err.message || "Save failed");
      } finally {
         setSaving(false);
      }
   }

   // -----------------------------------------
   // RENDER
   // -----------------------------------------
   return (
      <div className="max-w-4xl mx-auto p-6">
         <div className="flex items-center mb-4">
            <button
               onClick={() => navigate(-1)}
               className="mr-4 inline-flex items-center px-3 py-1.5 rounded bg-gray-100 hover:bg-gray-200"
            >
               <ChevronLeftIcon className="h-4 w-4 mr-2" /> Back
            </button>
            <h1 className="text-2xl font-semibold">Upload & Edit Invoice</h1>
         </div>

         {/* Upload Form */}
         <form onSubmit={handleUpload} className="mb-6">
            <div className="flex gap-3 items-center">
               <input
                  type="file"
                  accept="image/*,.pdf"
                  onChange={(e) => {
                     setFile(e.target.files?.[0] || null);
                     setParsed(null);
                     setItems([]);
                     setSuccess(null);
                  }}
                  className="border p-2 rounded"
               />

               <button
                  type="submit"
                  disabled={!file || parsing}
                  className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
               >
                  {parsing ? "Parsing..." : "Parse (OCR)"}
               </button>

               <div className="text-sm text-gray-500 ml-auto">
                  OCR confidence: <strong>{ocrConfidence ?? "n/a"}</strong>
               </div>
            </div>
         </form>

         {/* Messages */}
         {error && <div className="bg-red-50 text-red-600 p-3 rounded mb-4">{error}</div>}
         {success && (
            <div className="bg-green-50 text-green-700 p-3 rounded mb-4">
               Saved ✓ — bill id: {success.bill_id}
            </div>
         )}

         {/* Parsed Data Editor */}
         {parsed && (
            <div className="bg-white shadow rounded p-4">
               {/* Merchant + Date */}
               <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                     <label className="block text-sm font-medium text-gray-700">Merchant</label>
                     <input
                        className="mt-1 block w-full border rounded px-2 py-1"
                        value={merchant}
                        onChange={(e) => setMerchant(e.target.value)}
                     />
                  </div>
                  <div>
                     <label className="block text-sm font-medium text-gray-700">Bill Date</label>
                     <input
                        type="date"
                        className="mt-1 block w-full border rounded px-2 py-1"
                        value={date || ""}
                        onChange={(e) => setDate(e.target.value)}
                     />
                  </div>
               </div>

               {/* Items Table */}
               <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                     <thead className="bg-gray-50">
                        <tr>
                           <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Item</th>
                           <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Qty</th>
                           <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Unit Price</th>
                           <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Line Total</th>
                           <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Actions</th>
                        </tr>
                     </thead>
                     <tbody className="bg-white divide-y divide-gray-200">
                        {items.map((it, idx) => {
                           const lineTotal = (parseFloat(it.qty) || 0) * (parseFloat(it.unit_price) || 0);

                           return (
                              <tr key={idx} className="hover:bg-gray-50">
                                 <td className="px-3 py-2">
                                    <input
                                       type="text"
                                       value={it.name}
                                       onChange={(e) => updateItem(idx, "name", e.target.value)}
                                       className="w-full border rounded px-2 py-1"
                                    />
                                 </td>

                                 <td className="px-3 py-2 text-center">
                                    <input
                                       type="number"
                                       min="0"
                                       value={it.qty}
                                       onChange={(e) => updateItem(idx, "qty", e.target.value)}
                                       className="w-20 border rounded px-2 py-1 text-center"
                                    />
                                 </td>

                                 <td className="px-3 py-2 text-right">
                                    <input
                                       type="number"
                                       step="0.01"
                                       value={it.unit_price}
                                       onChange={(e) => updateItem(idx, "unit_price", e.target.value)}
                                       className="w-32 border rounded px-2 py-1 text-right"
                                    />
                                 </td>

                                 <td className="px-3 py-2 text-right">
                                    ₹{lineTotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                 </td>

                                 <td className="px-3 py-2 text-center">
                                    <button
                                       onClick={() => removeRow(idx)}
                                       className="inline-flex items-center px-2 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100"
                                    >
                                       <TrashIcon className="h-4 w-4" />
                                    </button>
                                 </td>
                              </tr>
                           );
                        })}
                     </tbody>
                  </table>
               </div>

               {/* Footer Actions */}
               <div className="flex items-center justify-between mt-4">
                  <button
                     type="button"
                     onClick={addRow}
                     className="inline-flex items-center px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded"
                  >
                     <PlusIcon className="h-4 w-4 mr-2" /> Add item
                  </button>

                  <div className="text-right space-y-2">
                     <div className="text-sm text-gray-600">
                        Subtotal: ₹{computeTotal().toLocaleString(undefined, { minimumFractionDigits: 2 })}
                     </div>

                     <div>
                        <label className="text-sm text-gray-600 mr-2">Final total override (optional)</label>
                        <input
                           type="number"
                           step="0.01"
                           value={totalOverride ?? ""}
                           onChange={(e) =>
                              setTotalOverride(e.target.value === "" ? null : Number(e.target.value))
                           }
                           className="border rounded px-2 py-1 w-40"
                        />
                     </div>

                     <button
                        onClick={handleSave}
                        disabled={saving}
                        className="mt-2 px-5 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                     >
                        {saving ? "Saving..." : "Save Bill"}
                     </button>
                  </div>
               </div>

               {/* Raw OCR */}
               <div className="mt-3 text-sm text-gray-500">
                  <strong>Raw OCR:</strong>
                  <pre className="whitespace-pre-wrap max-h-40 overflow-auto text-xs bg-gray-50 p-2 rounded mt-2">
                     {parsed.raw_text || "—"}
                  </pre>
               </div>
            </div>
         )}
      </div>
   );
}
