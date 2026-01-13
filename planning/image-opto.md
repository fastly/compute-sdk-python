# Image Optimization API Design

## Overview

Design for the Image Optimization API, allowing programmatic transformation of images via Fastly's Image Optimizer.

## WIT Interface Reference

```wit
interface image-optimizer {
  use http-body.{body};
  use http-req.{request};
  use http-resp.{response-with-body};
  use backend.{backend};

  record image-optimizer-transform-options {
    sdk-claims-opts: option<string>,
    extra: option<borrow<extra-image-optimizer-transform-options>>,
  }

  transform-image-optimizer-request: func(
    origin-image-request: borrow<request>,
    origin-image-request-body: option<body>,
    origin-image-request-backend: borrow<backend>,
    io-transform-options: image-optimizer-transform-options,
  ) -> result<response-with-body, error>;
}
```

Generated stubs: `stubs/wit_world/imports/image_optimizer.py`

## API Design

```python
from typing import Optional

class ImageOptimizer:
    """Interface to Fastly Image Optimizer."""
    
    @staticmethod
    def transform(
        request: 'Request',
        backend: str,
        body: Optional['Body'] = None,
        options: Optional[dict] = None
    ) -> 'Response':
        """Transform an image request using Fastly IO.
        
        Args:
            request: The request containing image parameters (query string)
            backend: The backend to fetch the original image from
            body: Optional request body
            options: Additional transform options
            
        Returns:
            Response containing the transformed image
        """
        pass
```

## Usage Examples

```python
from fastly_compute import ImageOptimizer, Request

def handle_image(req):
    # Create a request for the original image with IO params
    # e.g. /image.jpg?width=300&format=webp
    io_req = Request("GET", "/image.jpg?width=300&format=webp")
    
    # Transform using IO
    resp = ImageOptimizer.transform(io_req, backend="origin_images")
    
    return resp
```

## Deferred Features

- **Parameter Builders**: Helper classes to build IO query strings (e.g. `ImageOptions().width(300)`). Users should construct query strings manually or use standard URL tools.

## Implementation Notes

1.  **Backend**: Must be a valid backend capable of serving the source image.
2.  **Request**: The request URI's query parameters control the transformation.
