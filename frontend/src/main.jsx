import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { ArrowRight, Minus, Plus, Search, ShoppingBag, X } from 'lucide-react'
import './style.css'
import './responsive.css'

const API = '/api'
const money = (value, currency = 'PKR') => `${currency} ${Number(value || 0).toLocaleString()}`
let csrfToken = ''

async function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = { ...(options.headers || {}) }
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    if (!csrfToken) {
      const tokenResponse = await fetch(`${API}/csrf-token`, { credentials: 'include' })
      const tokenBody = await tokenResponse.text()
      let tokenData
      try {
        tokenData = JSON.parse(tokenBody)
      } catch {
        throw new Error(`CSRF endpoint returned HTTP ${tokenResponse.status}`)
      }
      csrfToken = tokenData.csrf_token
    }
    headers['X-CSRFToken'] = csrfToken
  }
  const response = await fetch(`${API}${path}`, { credentials: 'include', ...options, headers })
  const body = await response.text()
  let data
  try {
    data = JSON.parse(body)
  } catch {
    throw new Error(`Request failed with HTTP ${response.status}`)
  }
  if (!response.ok) throw new Error(data.message || 'Something went wrong')
  return data
}

function Header({ count, onSearch }) {
  const [query, setQuery] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const closeMenu = () => setMenuOpen(false)
  const closeSearch = () => setSearchOpen(false)
  useEffect(() => {
    document.body.style.overflow = menuOpen || searchOpen ? 'hidden' : ''
    const onKeyDown = event => {
      if (event.key === 'Escape') {
        setMenuOpen(false)
        setSearchOpen(false)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [menuOpen, searchOpen])
  const navigationLinks = [
    { label: 'Home', href: '#/' },
    { label: 'Shop', href: '#/shop' },
    { label: 'About', href: 'http://127.0.0.1:5000/about' },
    { label: 'Contact', href: 'http://127.0.0.1:5000/contact' },
  ]
  const submitSearch = event => { event.preventDefault(); if (!query.trim()) return; onSearch(query.trim()); closeSearch() }
  const searchTerms = ['Digital zikar', 'General', 'Tasbeeh', 'Accessories']
  return <><header className="header"><button className="menu-toggle" type="button" onClick={() => setMenuOpen(open => !open)} aria-expanded={menuOpen} aria-controls="mobile-sidebar" aria-label="Toggle navigation"><span/><span/><span/></button><a className="brand" href="#/" onClick={closeMenu}>BANTA <i>BAZAR</i></a><nav id="site-navigation">{navigationLinks.map(item => <a key={item.href} href={item.href} onClick={closeMenu}>{item.label}</a>)}</nav><button className="search-trigger" type="button" onClick={() => setSearchOpen(true)} aria-label="Open search"><Search size={18}/></button><a className="cart-link" href="#/cart" onClick={closeMenu}><ShoppingBag size={18}/><span>{count}</span></a></header><div className={`search-overlay ${searchOpen ? 'is-open' : ''}`} aria-hidden={!searchOpen}><div className="search-overlay-top"><button className="search-close" type="button" onClick={closeSearch} aria-label="Close search"><X size={18}/></button></div><div className="search-overlay-content"><p className="sidebar-label">Search the collection</p><form onSubmit={submitSearch}><input autoFocus={searchOpen} value={query} onChange={event => setQuery(event.target.value)} placeholder="Search products..."/></form><div className="search-suggestions">{searchTerms.map(term => <button key={term} type="button" onClick={() => { setQuery(term); onSearch(term); closeSearch() }}>{term}</button>)}</div></div></div><div className={`mobile-sidebar-backdrop ${menuOpen ? 'is-open' : ''}`} onClick={closeMenu}/><aside id="mobile-sidebar" className={`mobile-sidebar ${menuOpen ? 'is-open' : ''}`} aria-hidden={!menuOpen}><div className="mobile-sidebar-header"><a className="brand" href="#/" onClick={closeMenu}>BANTA <i>BAZAR</i></a><button className="sidebar-close" type="button" onClick={closeMenu} aria-label="Close navigation"><X size={18}/></button></div><nav className="mobile-sidebar-nav">{navigationLinks.map((item, index) => <a key={item.href} href={item.href} onClick={closeMenu} style={{ '--sidebar-index': index }}>{item.label}</a>)}</nav><div className="mobile-sidebar-actions"><a href="#/cart" onClick={closeMenu}>View cart</a><a href="#/shop" onClick={closeMenu}>Browse products</a></div></aside></>
}

function ProductCard({ product, add }) {
  const image = product.image || 'https://images.pexels.com/photos/1714208/pexels-photo-1714208.jpeg?auto=compress&cs=tinysrgb&w=700'
  return <article className="product-card"><a href={`/product/${product.id}`} className="product-image"><img src={image} alt={product.name}/>{product.sale_percent > 0 && <b>-{product.sale_percent}%</b>}</a><p className="eyebrow">{product.category}</p><div className="product-line"><a href={`/product/${product.id}`}><h3>{product.name}</h3></a><strong>{money(product.sale_price || product.price, product.currency)}</strong></div><p className="muted">{product.description || 'Reliable everyday essentials for your space.'}</p><button className="button dark small" onClick={() => add(product.id)} disabled={!product.quantity}>Add to cart <ArrowRight size={14}/></button></article>
}

function Shop({ products, categories, add, initialQuery = '' }) {
  const [category, setCategory] = useState('')
  const [query, setQuery] = useState(initialQuery)
  const visible = products.filter(product => (!category || product.category === category) && (!query || product.name.toLowerCase().includes(query.toLowerCase())))
  return <main className="page"><div className="page-heading"><div><p className="eyebrow">Banta Bazar collection</p><h1>Useful things,<br/><em>beautifully chosen.</em></h1></div><p className="intro">Modern electronics and daily essentials selected for dependable performance and good living.</p></div><div className="shop-layout"><aside className="shop-sidebar"><div><p className="sidebar-label">Search</p><input className="sidebar-search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search the collection"/></div><div><p className="sidebar-label">Category</p><ul className="category-list"><li><button className={!category ? 'is-active' : ''} onClick={() => setCategory('')}>Everything</button></li>{categories.map(item => <li key={item}><button className={category === item ? 'is-active' : ''} onClick={() => setCategory(item)}>{item}</button></li>)}</ul></div></aside><div className="shop-results"><div className="filters"><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search the collection"/><select value={category} onChange={event => setCategory(event.target.value)}><option value="">All categories</option>{categories.map(item => <option key={item}>{item}</option>)}</select></div><div className="product-grid">{visible.map(product => <ProductCard key={product.id} product={product} add={add}/>)}</div>{!visible.length && <p className="empty">No products match that search.</p>}</div></div></main>
}

function Home({ products, add, heroSlides }) {
  const [activeSlide, setActiveSlide] = useState(0)
  const slides = heroSlides.length ? heroSlides.slice(0, 1) : [{
    eyebrow: 'Banta Bazar / everyday essentials',
    headline: 'Good products for real life.',
    description: 'Thoughtful electronics and accessories, honest prices, and the dependable service your everyday shopping deserves.',
    image: products[0]?.image || 'https://images.pexels.com/photos/1714208/pexels-photo-1714208.jpeg?auto=compress&cs=tinysrgb&w=1000',
    category: '',
  }]
  const slide = slides[activeSlide % slides.length]
  const shopHref = slide.category ? `/shop?category=${encodeURIComponent(slide.category)}` : '/shop'

  useEffect(() => {
    setActiveSlide(0)
  }, [heroSlides])

  return <main><section className="hero"><div className="hero-copy"><p className="eyebrow">{slide.eyebrow || 'Featured'}</p><h1>{slide.headline || 'Welcome to Banta Bazar'}</h1><p className="intro">{slide.description || 'Shop trusted electronics and accessories with dependable service.'}</p><a className="button dark" href={shopHref}>Shop the collection <ArrowRight size={16}/></a><div className="stats"><span><b>{slides.length}</b> curated picks</span><span><b>Fast</b> local delivery</span><span><b>Easy</b> returns</span></div></div><div className="hero-image"><img src={slide.image || products[0]?.image || 'https://images.pexels.com/photos/1714208/pexels-photo-1714208.jpeg?auto=compress&cs=tinysrgb&w=1000'} alt={slide.headline || 'Featured Banta Bazar product'}/></div></section><section className="section"><div className="section-title"><div><p className="eyebrow">Featured now</p><h2>Made for the everyday.</h2></div><a className="link" href="#/shop">View all <ArrowRight size={15}/></a></div><div className="product-grid">{products.slice(0, 4).map(product => <ProductCard key={product.id} product={product} add={add}/>)}</div></section></main>
}

function Product({ product, add }) {
  const [image, setImage] = useState(product.images?.[0] || product.image)
  return <main className="page"><a className="back link" href="#/shop">← Back to shop</a><div className="detail"><div><img className="detail-image" src={image} alt={product.name}/><div className="thumbs">{(product.images?.length ? product.images : [product.image]).map(item => <button key={item} onClick={() => setImage(item)}><img src={item} alt=""/></button>)}</div></div><div className="detail-copy"><p className="eyebrow">{product.category} {product.sale_percent ? ` / -${product.sale_percent}%` : ''}</p><h1>{product.name}</h1><p className="price">{money(product.sale_price || product.price, product.currency)}</p><p className="intro">{product.description || 'A practical choice for shoppers who want dependable value and everyday performance.'}</p><p className={product.quantity ? 'stock good' : 'stock'}>{product.quantity ? `${product.quantity} available` : 'Out of stock'}</p><button className="button dark" onClick={() => add(product.id)} disabled={!product.quantity}>Add to cart <ShoppingBag size={16}/></button><div className="detail-note"><b>Quality checked</b><span>Secure checkout · clear pricing · helpful support</span></div></div></div></main>
}

function Cart({ cart, update }) {
  return <main className="page"><div className="page-heading"><div><p className="eyebrow">Your selection</p><h1>Your bag.</h1></div><a className="link" href="#/shop">Continue shopping</a></div>{!cart.items.length ? <div className="empty"><ShoppingBag size={36}/><h2>Your bag is empty</h2><a className="button dark" href="#/shop">Browse products <ArrowRight size={16}/></a></div> : <div className="cart-layout"><div className="cart-items">{cart.items.map(item => <article className="cart-item" key={item.id}><img src={item.image} alt={item.name}/><div><p className="eyebrow">{item.category}</p><h3>{item.name}</h3><p>{money(item.price, 'PKR')} each</p><div className="quantity"><button onClick={() => update(item.id, item.quantity - 1)}><Minus size={14}/></button><span>{item.quantity}</span><button onClick={() => update(item.id, item.quantity + 1)}><Plus size={14}/></button></div></div><strong>{item.item_total}</strong><button className="icon-button" onClick={() => update(item.id, 0)} aria-label="Remove"><X size={16}/></button></article>)}</div><aside className="summary"><p className="eyebrow">Order summary</p><h2>{money(cart.total)}</h2><p className="muted">Delivery charges and final details are confirmed at checkout.</p><a className="button dark full" href="http://127.0.0.1:5000/checkout">Proceed to checkout <ArrowRight size={16}/></a></aside></div>}</main>
}

function Footer() {
  return <footer className="footer"><div className="footer-inner"><div className="footer-col"><h3>Banta bazar</h3><p>Your trusted online electronics store. Best prices, best quality.</p></div><div className="footer-col"><h4>Quick Links</h4><a href="#/">Home</a><a href="http://127.0.0.1:5000/about">About Us</a><a href="http://127.0.0.1:5000/contact">Contact</a><a href="/admin/dashboard">Admin</a></div><div className="footer-col"><h4>Contact</h4><p>Email: info@bantabazar.com</p><p>Phone: +92 32 00 33 77 20</p></div></div><div className="footer-bottom"><p>&copy; 2026 banta bazar. All rights reserved.</p></div></footer>
}

function App() {
  const [products, setProducts] = useState([]); const [categories, setCategories] = useState([]); const [heroSlides, setHeroSlides] = useState([]); const [cart, setCart] = useState({ items: [], count: 0, total: 0 }); const [selected, setSelected] = useState(null); const [search, setSearch] = useState(''); const [hash, setHash] = useState(window.location.hash); const [pathname, setPathname] = useState(window.location.pathname)
  const load = () => Promise.all([request('/products'), request('/cart'), request('/homepage')]).then(([catalog, bag, homepage]) => { setProducts(catalog.products); setCategories(catalog.categories); setHeroSlides(homepage.hero_slides || []); setCart(bag) })
  useEffect(() => { load().catch(console.error) }, [])
  useEffect(() => { const onLocationChange = () => { setHash(window.location.hash); setPathname(window.location.pathname) }; window.addEventListener('hashchange', onLocationChange); window.addEventListener('popstate', onLocationChange); return () => { window.removeEventListener('hashchange', onLocationChange); window.removeEventListener('popstate', onLocationChange) } }, [])
  useEffect(() => {
    const shopHash = window.location.hash.match(/^#\/shop(\?.*)?$/)
    if (shopHash) {
      window.history.replaceState({}, '', `/shop${shopHash[1] || ''}`)
      setHash('')
      setPathname('/shop')
    }
    document.querySelectorAll('a[href^="#/shop"]').forEach(link => {
      link.setAttribute('href', link.getAttribute('href').replace(/^#/, ''))
    })
  }, [categories, products, selected, cart])
  useEffect(() => { const match = hash.match(/#\/product\/(\d+)/); if (match) request(`/products/${match[1]}`).then(data => setSelected(data.product)).catch(console.error); else setSelected(null) }, [hash])
  const add = id => request('/cart', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product_id: id }) }).then(setCart).catch(error => alert(error.message))
  const update = (id, quantity) => request(`/cart/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ quantity }) }).then(setCart).catch(error => alert(error.message))
  const path = pathname === '/shop' ? '/shop' : hash.split('?')[0]
  return <><Header count={cart.count} onSearch={value => { setSearch(value); window.history.pushState({}, '', '/shop'); setPathname('/shop') }}/>{selected ? <Product product={selected} add={add}/> : path === '#/cart' ? <Cart cart={cart} update={update}/> : path === '/shop' ? <Shop products={products} categories={categories} add={add} initialQuery={search}/> : <Home products={products} add={add} heroSlides={heroSlides}/>}<Footer/></>
}

createRoot(document.getElementById('root')).render(<StrictMode><App/></StrictMode>)
