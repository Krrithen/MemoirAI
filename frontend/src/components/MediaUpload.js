import React from "react";

const MediaUpload = ({ onMediaSelect }) => {
  const handleChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onMediaSelect(file);
    }
  };

  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Upload Image or Video (optional)
      </label>
      <input
        type="file"
        accept="image/*,video/*"
        onChange={handleChange}
        className="block w-full text-sm text-gray-500
          file:mr-4 file:py-2 file:px-4
          file:rounded-lg file:border-0
          file:text-sm file:font-semibold
          file:bg-blue-50 file:text-blue-700
          hover:file:bg-blue-100"
      />
    </div>
  );
};

export default MediaUpload;
