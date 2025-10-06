# Story: E-commerce Integration

**Story ID**: STORY-010
**Epic**: EPIC-002 (Core Productivity Suite)
**Type**: New Feature
**Priority**: P1 (High)
**Points**: 8
**Sprint**: 8-9
**Status**: Ready for Development

## User Story

**As a** user
**I want** to purchase recommended books directly from chat responses
**So that** I can deepen my knowledge without leaving the platform

## Context

E-commerce integration transforms the chatbot from a free tool into a revenue-generating platform. By seamlessly embedding purchase options within chat responses, we create a frictionless path from learning about a topic to purchasing the authoritative MC Press book. This feature directly supports MC Press's business model and creates a win-win: users get relevant resources, MC Press generates sales.

## Current State

### Existing System
- **Chat Interface**: Q&A with MC Press book content
- **Knowledge Base**: 110+ MC Press books referenced
- **AI Responses**: Include book titles and authors
- **Vector Store**: Book metadata includes titles, authors, ISBNs
- **Database**: Books table with mc_press_url field (may be empty)

### Gap Analysis
- No purchase CTAs in chat responses
- No pricing information displayed
- No shopping cart functionality
- No discount code system
- No purchase tracking/analytics
- No bundle recommendations
- No integration with MC Press store API

## Acceptance Criteria

### Core E-commerce Features
- [ ] "Buy Now" buttons in chat responses when books are referenced
- [ ] Real-time pricing display from MC Press Store API
- [ ] Product page preview on hover/click
- [ ] Add to cart functionality
- [ ] Shopping cart widget (persistent across sessions)
- [ ] Checkout redirect to MC Press Store
- [ ] Order tracking (after purchase)

### Smart Recommendations
- [ ] Bundle recommendations (related books)
- [ ] "Customers also bought" suggestions
- [ ] Context-aware recommendations based on conversation
- [ ] Learning path book sequences
- [ ] Beginner/Intermediate/Advanced book filtering

### Pricing & Discounts
- [ ] Display current pricing (print, ebook, bundle)
- [ ] Show subscriber discounts (10-20% off)
- [ ] Apply discount codes automatically
- [ ] Display savings prominently
- [ ] Special promotions/deals highlighting

### Analytics & Tracking
- [ ] Track book impressions in chat
- [ ] Track "Buy Now" click-through rate
- [ ] Track conversions (chatbot → purchase)
- [ ] Track bundle recommendation acceptance
- [ ] Revenue attribution to chatbot

## Technical Design

### E-commerce Architecture

```
Chat Response → Book Detection → MC Press API → Product Display → Cart → Checkout
                                      ↓                              ↓
                                  Pricing Data                  MC Press Store
                                  Stock Status
                                  Promotions
```

### MC Press Store API Integration

```python
class MCPressStoreAPI:
    """Integration with MC Press Store API"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session = aiohttp.ClientSession()

    async def get_product_details(
        self,
        isbn: str
    ) -> ProductDetails:
        """Get product details by ISBN"""

        response = await self.session.get(
            f"{self.base_url}/api/products/{isbn}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        data = await response.json()

        return ProductDetails(
            isbn=data['isbn'],
            title=data['title'],
            author=data['author'],
            price_print=data['price_print'],
            price_ebook=data['price_ebook'],
            price_bundle=data.get('price_bundle'),
            in_stock=data['in_stock'],
            product_url=data['url'],
            cover_image=data['cover_image'],
            description=data['description']
        )

    async def get_bulk_pricing(
        self,
        isbns: List[str]
    ) -> Dict[str, ProductPricing]:
        """Get pricing for multiple products"""

        response = await self.session.post(
            f"{self.base_url}/api/products/bulk-pricing",
            json={"isbns": isbns},
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        data = await response.json()
        return {
            item['isbn']: ProductPricing(**item)
            for item in data['products']
        }

    async def get_related_products(
        self,
        isbn: str,
        limit: int = 5
    ) -> List[ProductSummary]:
        """Get related/recommended products"""

        response = await self.session.get(
            f"{self.base_url}/api/products/{isbn}/related",
            params={"limit": limit},
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        data = await response.json()
        return [ProductSummary(**item) for item in data['products']]

    async def apply_discount_code(
        self,
        code: str,
        cart_items: List[str]
    ) -> DiscountResult:
        """Validate and apply discount code"""

        response = await self.session.post(
            f"{self.base_url}/api/discounts/validate",
            json={"code": code, "items": cart_items},
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        data = await response.json()
        return DiscountResult(**data)

    async def create_checkout_session(
        self,
        user_id: str,
        cart_items: List[CartItem],
        discount_code: Optional[str] = None
    ) -> CheckoutSession:
        """Create checkout session at MC Press Store"""

        response = await self.session.post(
            f"{self.base_url}/api/checkout/create",
            json={
                "user_id": user_id,
                "items": [item.dict() for item in cart_items],
                "discount_code": discount_code,
                "source": "chatbot",
                "return_url": f"{FRONTEND_URL}/order-confirmation"
            },
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        data = await response.json()
        return CheckoutSession(
            session_id=data['session_id'],
            checkout_url=data['checkout_url'],
            expires_at=data['expires_at']
        )
```

### Book Detection in Chat Responses

```python
class BookReferenceDetector:
    """Detect book references in AI responses"""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    async def detect_book_references(
        self,
        response_text: str,
        context_chunks: List[Chunk]
    ) -> List[BookReference]:
        """Detect which books were referenced in response"""

        referenced_books = []

        # Extract book metadata from context chunks
        for chunk in context_chunks:
            book_info = {
                'title': chunk.metadata.get('title'),
                'author': chunk.metadata.get('author'),
                'isbn': chunk.metadata.get('isbn'),
                'mc_press_url': chunk.metadata.get('mc_press_url')
            }

            # Check if book is mentioned in response
            if self._is_book_mentioned(response_text, book_info):
                referenced_books.append(BookReference(**book_info))

        # Deduplicate
        unique_books = self._deduplicate_books(referenced_books)

        return unique_books

    def _is_book_mentioned(
        self,
        text: str,
        book_info: Dict[str, str]
    ) -> bool:
        """Check if book is mentioned in text"""

        text_lower = text.lower()

        # Check for title mention
        if book_info['title'].lower() in text_lower:
            return True

        # Check for author mention with context
        if book_info['author'].lower() in text_lower:
            # Verify it's in book context
            if any(keyword in text_lower for keyword in [
                'book', 'guide', 'manual', 'reference', 'by '
            ]):
                return True

        return False

    async def get_contextual_recommendations(
        self,
        conversation_history: List[Message],
        current_topic: str
    ) -> List[BookReference]:
        """Get book recommendations based on conversation context"""

        # Analyze conversation to understand user's level and interests
        user_profile = await self._analyze_user_profile(
            conversation_history
        )

        # Search for relevant books
        query = f"{current_topic} {user_profile.level} {user_profile.interest_area}"

        books = await self.vector_store.search_books(
            query,
            k=5,
            filters={
                'difficulty': user_profile.level
            }
        )

        return books
```

### Shopping Cart System

```python
class ShoppingCart(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[CartItem] = []
    discount_code: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=30)
    )

class CartItem(BaseModel):
    isbn: str
    title: str
    format: str  # 'print', 'ebook', 'bundle'
    price: float
    quantity: int = 1
    discount_amount: float = 0.0

class ShoppingCartService:
    """Manage shopping cart"""

    async def add_to_cart(
        self,
        user_id: str,
        isbn: str,
        format: str = 'print'
    ) -> ShoppingCart:
        """Add item to cart"""

        # Get or create cart
        cart = await self._get_or_create_cart(user_id)

        # Get product details
        product = await self.store_api.get_product_details(isbn)

        # Determine price based on format
        price = {
            'print': product.price_print,
            'ebook': product.price_ebook,
            'bundle': product.price_bundle
        }[format]

        # Check if item already in cart
        existing_item = next(
            (item for item in cart.items
             if item.isbn == isbn and item.format == format),
            None
        )

        if existing_item:
            existing_item.quantity += 1
        else:
            # Add new item
            cart.items.append(CartItem(
                isbn=isbn,
                title=product.title,
                format=format,
                price=price
            ))

        # Apply discounts
        await self._apply_discounts(cart)

        # Save cart
        await self._save_cart(cart)

        # Track analytics
        await self._track_add_to_cart(user_id, isbn)

        return cart

    async def apply_discount_code(
        self,
        user_id: str,
        code: str
    ) -> ShoppingCart:
        """Apply discount code to cart"""

        cart = await self._get_cart(user_id)

        # Validate discount code
        discount_result = await self.store_api.apply_discount_code(
            code,
            [item.isbn for item in cart.items]
        )

        if discount_result.valid:
            cart.discount_code = code

            # Apply discount amounts
            for item in cart.items:
                if item.isbn in discount_result.discounted_items:
                    item.discount_amount = discount_result.discounts[item.isbn]

            await self._save_cart(cart)

        return cart

    async def checkout(
        self,
        user_id: str
    ) -> CheckoutSession:
        """Create checkout session"""

        cart = await self._get_cart(user_id)

        # Create checkout session at MC Press Store
        session = await self.store_api.create_checkout_session(
            user_id,
            cart.items,
            cart.discount_code
        )

        # Track conversion funnel
        await self._track_checkout_initiated(user_id, cart)

        return session
```

### Enhanced Chat Response with E-commerce

```python
class EcommerceEnhancedChatHandler:
    """Chat handler with e-commerce integration"""

    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_history: List[Message]
    ) -> EnhancedChatResponse:
        """Process message with e-commerce enhancements"""

        # Get AI response (existing functionality)
        ai_response = await self.chat_handler.get_response(
            message,
            conversation_history
        )

        # Detect book references
        book_references = await self.book_detector.detect_book_references(
            ai_response.text,
            ai_response.context_chunks
        )

        # Get pricing for referenced books
        if book_references:
            isbns = [book.isbn for book in book_references if book.isbn]
            pricing_data = await self.store_api.get_bulk_pricing(isbns)
        else:
            pricing_data = {}

        # Get contextual recommendations
        recommendations = await self.book_detector.get_contextual_recommendations(
            conversation_history,
            ai_response.topic
        )

        # Build enhanced response
        enhanced_response = EnhancedChatResponse(
            text=ai_response.text,
            book_references=[
                {
                    **book.dict(),
                    'pricing': pricing_data.get(book.isbn)
                }
                for book in book_references
            ],
            recommendations=[
                {
                    **book.dict(),
                    'pricing': pricing_data.get(book.isbn)
                }
                for book in recommendations
            ],
            context_chunks=ai_response.context_chunks
        )

        # Track book impressions
        await self._track_book_impressions(
            user_id,
            book_references + recommendations
        )

        return enhanced_response
```

### Frontend Components

#### Product Display Components

```typescript
interface ProductCard {
  isbn: string
  title: string
  author: string
  pricing: {
    print: number
    ebook: number
    bundle?: number
  }
  discount?: {
    amount: number
    percentage: number
  }
  coverImage: string
  productUrl: string
}

// Components
const BookReferenceCard = ({ book, onAddToCart }) => (
  <div className="book-reference-card">
    <img src={book.coverImage} alt={book.title} />
    <div className="book-info">
      <h4>{book.title}</h4>
      <p>by {book.author}</p>
      <div className="pricing">
        <span className="price">${book.pricing.print}</span>
        {book.discount && (
          <span className="savings">Save ${book.discount.amount}</span>
        )}
      </div>
      <button onClick={() => onAddToCart(book.isbn, 'print')}>
        Add to Cart
      </button>
      <a href={book.productUrl} target="_blank">View Details</a>
    </div>
  </div>
)

const ShoppingCartWidget = ({ cart, onCheckout }) => (
  <div className="cart-widget">
    <div className="cart-header">
      <FiShoppingCart />
      <span>{cart.items.length} items</span>
    </div>
    <div className="cart-items">
      {cart.items.map(item => (
        <CartItemRow key={`${item.isbn}-${item.format}`} item={item} />
      ))}
    </div>
    <div className="cart-total">
      <span>Total:</span>
      <span>${calculateTotal(cart)}</span>
    </div>
    <button onClick={onCheckout}>Checkout</button>
  </div>
)
```

### Database Schema

```sql
-- Shopping carts
CREATE TABLE IF NOT EXISTS shopping_carts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    items JSONB NOT NULL DEFAULT '[]',
    discount_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    UNIQUE(user_id)
);

-- E-commerce analytics
CREATE TABLE IF NOT EXISTS ecommerce_events (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'impression', 'click', 'add_to_cart', 'checkout', 'purchase'
    isbn TEXT,
    product_title TEXT,
    format TEXT,
    price FLOAT,
    discount_amount FLOAT,
    session_id TEXT,
    conversation_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Purchase attribution
CREATE TABLE IF NOT EXISTS chatbot_conversions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    total_amount FLOAT NOT NULL,
    items JSONB NOT NULL,
    conversation_id TEXT,
    last_book_impression_at TIMESTAMP,
    attribution_window_hours INTEGER DEFAULT 24,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_carts_user
ON shopping_carts(user_id);

CREATE INDEX IF NOT EXISTS idx_ecommerce_events_user
ON ecommerce_events(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_ecommerce_events_type
ON ecommerce_events(event_type, isbn, created_at);

CREATE INDEX IF NOT EXISTS idx_conversions_user
ON chatbot_conversions(user_id, created_at);
```

### API Endpoints

```python
# Cart operations
GET    /api/cart                       # Get user's cart
POST   /api/cart/add                   # Add item to cart
DELETE /api/cart/item/{isbn}/{format}  # Remove item
POST   /api/cart/discount              # Apply discount code
POST   /api/cart/checkout              # Create checkout session

# Product info
GET    /api/products/{isbn}            # Get product details
POST   /api/products/bulk              # Get multiple products
GET    /api/products/{isbn}/related    # Get related products

# Recommendations
GET    /api/recommendations            # Get personalized recommendations
POST   /api/recommendations/context    # Get context-based recommendations

# Analytics
POST   /api/analytics/track            # Track e-commerce event
GET    /api/analytics/revenue          # Revenue dashboard (admin)
```

## Implementation Tasks

### Backend Tasks
- [ ] Integrate MC Press Store API
- [ ] Create shopping cart service
- [ ] Build book reference detector
- [ ] Implement pricing cache
- [ ] Create discount code system
- [ ] Build recommendation engine
- [ ] Add analytics tracking
- [ ] Create checkout flow
- [ ] Implement conversion attribution
- [ ] Add revenue dashboards

### Frontend Tasks
- [ ] Create product display components
- [ ] Build shopping cart widget
- [ ] Implement "Buy Now" buttons in chat
- [ ] Add product preview modals
- [ ] Create checkout redirect flow
- [ ] Build recommendations carousel
- [ ] Add discount code input
- [ ] Implement cart persistence
- [ ] Create order confirmation page

### Integration Tasks
- [ ] Integrate with MC Press Store API
- [ ] Wire cart to chat responses
- [ ] Connect analytics tracking
- [ ] Test checkout flow end-to-end
- [ ] Validate discount codes
- [ ] Test conversion tracking

### Database Tasks
- [ ] Create shopping_carts table
- [ ] Create ecommerce_events table
- [ ] Create chatbot_conversions table
- [ ] Add indexes
- [ ] Create migration script

## Testing Requirements

### Unit Tests
- [ ] Book reference detection
- [ ] Cart operations (add/remove/update)
- [ ] Discount code validation
- [ ] Price calculation
- [ ] Analytics tracking

### Integration Tests
- [ ] MC Press API integration
- [ ] Complete cart flow
- [ ] Checkout session creation
- [ ] Discount application
- [ ] Conversion tracking

### E2E Tests
- [ ] Chat → book reference → add to cart
- [ ] Apply discount code
- [ ] Complete checkout
- [ ] Track purchase conversion
- [ ] View recommendations

## Success Metrics

- **Conversion Rate**: 5% of users make purchase
- **Click-Through Rate**: 20% click "Buy Now"
- **Average Order Value**: $50+
- **Cart Abandonment**: <70%
- **Revenue Attribution**: Track 80%+ of chatbot-driven sales
- **Recommendation Acceptance**: 10% of recommendations added to cart

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] MC Press API integration verified
- [ ] Code reviewed and approved
- [ ] Revenue tracking validated
- [ ] Documentation updated
- [ ] Deployed to staging
- [ ] UAT completed with MC Press team
- [ ] Production deployment successful
- [ ] Revenue dashboard operational

## Dependencies

- MC Press Store API access and documentation
- Product catalog with ISBNs
- Pricing and discount APIs
- Checkout/payment integration
- Analytics infrastructure

## Risks

- **Risk**: MC Press API downtime affects chatbot
  - **Mitigation**: Graceful degradation, cache pricing data, fallback to static links

- **Risk**: Pricing data out of sync
  - **Mitigation**: Real-time API calls, cache invalidation strategy

- **Risk**: Low conversion rate
  - **Mitigation**: A/B testing, optimize CTAs, improve recommendations

- **Risk**: Cart abandonment too high
  - **Mitigation**: Persistent cart, email reminders, discount incentives

## Future Enhancements

- Subscription upsell in cart
- Gift card support
- Wishlist functionality
- Price drop alerts
- Book bundles/learning paths as products
- Affiliate revenue sharing
- Integration with more e-commerce platforms

---

## Notes

This feature is critical for monetization. Focus on seamless UX - purchasing should feel natural within the learning flow, not forced.
