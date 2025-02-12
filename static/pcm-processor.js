class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.buffer = new Float32Array(0);
        this.port.onmessage = this.handleMessage.bind(this);
    }

    handleMessage(event) {
        const data = event.data;
        // Append new data to existing buffer
        const newBuffer = new Float32Array(this.buffer.length + data.length);
        newBuffer.set(this.buffer);
        newBuffer.set(data, this.buffer.length);
        this.buffer = newBuffer;
    }

    process(inputs, outputs) {
        const output = outputs[0];
        const channel = output[0];

        if (this.buffer.length >= channel.length) {
            // Copy data from buffer to output
            channel.set(this.buffer.slice(0, channel.length));
            // Keep remaining data in buffer
            this.buffer = this.buffer.slice(channel.length);
        } else {
            // Not enough data, output silence
            channel.fill(0);
        }

        return true;
    }
}

registerProcessor('pcm-processor', PCMProcessor); 