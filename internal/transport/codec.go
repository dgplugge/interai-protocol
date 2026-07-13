package transport

import (
	"bytes"
	"encoding/gob"

	"google.golang.org/grpc/encoding"
)

const CodecName = "interai-gob"

type GobCodec struct{}

func (GobCodec) Name() string {
	return CodecName
}

func (GobCodec) Marshal(v any) ([]byte, error) {
	var buf bytes.Buffer
	if err := gob.NewEncoder(&buf).Encode(v); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

func (GobCodec) Unmarshal(data []byte, v any) error {
	return gob.NewDecoder(bytes.NewReader(data)).Decode(v)
}

func init() {
	encoding.RegisterCodec(GobCodec{})
}
