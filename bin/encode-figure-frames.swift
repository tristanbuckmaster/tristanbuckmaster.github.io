// macOS alternative to ffmpeg. Compile with swiftc and pass a directory of
// zero-padded, sequential PNGs, the destination .mp4, and the frame rate.
import AVFoundation
import CoreGraphics
import CoreVideo
import Foundation
import ImageIO

struct EncoderError: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}

func readImage(_ url: URL) throws -> CGImage {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw EncoderError("Cannot read \(url.lastPathComponent)")
    }
    return image
}

func writeFrame(_ image: CGImage, adaptor: AVAssetWriterInputPixelBufferAdaptor,
                time: CMTime, writer: AVAssetWriter) throws {
    guard let pool = adaptor.pixelBufferPool else { throw EncoderError("Pixel-buffer pool unavailable") }
    var optional: CVPixelBuffer?
    guard CVPixelBufferPoolCreatePixelBuffer(nil, pool, &optional) == kCVReturnSuccess,
          let buffer = optional else { throw EncoderError("Pixel-buffer allocation failed") }
    let bitmap = CGBitmapInfo.byteOrder32Little.rawValue | CGImageAlphaInfo.noneSkipFirst.rawValue
    let locked = CVPixelBufferLockBaseAddress(buffer, [])
    guard locked == kCVReturnSuccess else { throw EncoderError("Pixel-buffer lock failed") }
    do {
        defer { CVPixelBufferUnlockBaseAddress(buffer, []) }
        guard let context = CGContext(data: CVPixelBufferGetBaseAddress(buffer),
                                      width: image.width, height: image.height,
                                      bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
                                      space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: bitmap) else {
            throw EncoderError("Cannot construct a drawing context")
        }
        context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
    }
    if !adaptor.append(buffer, withPresentationTime: time) {
        throw writer.error ?? EncoderError("Frame submission failed")
    }
}

func encode() throws {
    let args = CommandLine.arguments
    guard args.count == 4, let fps = Int32(args[3]), fps > 0 else {
        throw EncoderError("Usage: encode-figure-frames directory output.mp4 frames-per-second")
    }
    let directory = URL(fileURLWithPath: args[1], isDirectory: true)
    let destination = URL(fileURLWithPath: args[2])
    let frames = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        .filter { $0.pathExtension.lowercased() == "png" }.sorted { $0.lastPathComponent < $1.lastPathComponent }
    guard let first = frames.first else { throw EncoderError("No PNG frames in \(directory.path)") }
    let image = try readImage(first)
    guard image.width.isMultiple(of: 2), image.height.isMultiple(of: 2) else {
        throw EncoderError("H.264 output needs even frame dimensions")
    }

    let width = image.width, height = image.height
    let writer = try AVAssetWriter(outputURL: destination, fileType: .mp4)
    writer.shouldOptimizeForNetworkUse = true
    let options: [String: Any] = [
        AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: image.width, AVVideoHeightKey: image.height,
        AVVideoCompressionPropertiesKey: [
            AVVideoAverageBitRateKey: 1_450_000,
            AVVideoProfileLevelKey: AVVideoProfileLevelH264MainAutoLevel,
            AVVideoMaxKeyFrameIntervalKey: Int(fps),
            AVVideoAllowFrameReorderingKey: false
        ]
    ]
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: options)
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
        kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA),
        kCVPixelBufferWidthKey as String: image.width, kCVPixelBufferHeightKey as String: image.height
    ])
    guard writer.canAdd(input) else { throw EncoderError("H.264 video input unavailable") }
    writer.add(input)
    guard writer.startWriting() else { throw writer.error ?? EncoderError("Encoder did not start") }
    writer.startSession(atSourceTime: .zero)
    for (index, frame) in frames.enumerated() {
        while !input.isReadyForMoreMediaData {
            guard writer.status == .writing else { throw writer.error ?? EncoderError("Encoder stopped") }
            Thread.sleep(forTimeInterval: 0.005)
        }
        try autoreleasepool {
            let image = try readImage(frame)
            guard image.width == width, image.height == height else {
                throw EncoderError("Frame dimensions changed in \(frame.lastPathComponent)")
            }
            try writeFrame(image, adaptor: adaptor, time: CMTime(value: Int64(index), timescale: fps), writer: writer)
        }
    }
    writer.endSession(atSourceTime: CMTime(value: Int64(frames.count), timescale: fps))
    input.markAsFinished()
    let finished = DispatchSemaphore(value: 0)
    writer.finishWriting { finished.signal() }
    finished.wait()
    guard writer.status == .completed else { throw writer.error ?? EncoderError("Incomplete MP4") }
    print("Encoded \(frames.count) frames at \(fps) fps to \(destination.path)")
}

do { try encode() }
catch { FileHandle.standardError.write(Data((error.localizedDescription + "\n").utf8)); exit(1) }
