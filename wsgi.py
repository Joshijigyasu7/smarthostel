import os
import sys
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("Starting WSGI Application")
logger.info("=" * 60)

try:
    logger.info("Python version: " + sys.version)
    
    # Check environment
    logger.info("Environment check:")
    logger.info(f"  FLASK_ENV: {os.environ.get('FLASK_ENV', 'not set')}")
    mongodb_uri = os.environ.get('MONGODB_URI', 'not set')
    if mongodb_uri != 'not set':
        logger.info(f"  MONGODB_URI: {mongodb_uri[:60]}...")
    else:
        logger.info(f"  MONGODB_URI: not set")
    logger.info(f"  PORT: {os.environ.get('PORT', '8000')}")
    
    # Import app
    logger.info("\nImporting Flask app...")
    from app import app
    logger.info("✓ Flask app imported successfully")
    
    # Check routes
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    logger.info(f"✓ Routes registered: {len(routes)} routes")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ WSGI application ready")
    logger.info("=" * 60)
    
except Exception as e:
    logger.error("=" * 60)
    logger.error(f"✗ ERROR during startup: {str(e)}")
    logger.error("=" * 60)
    import traceback
    logger.error(traceback.format_exc())
    raise

# Export app for gunicorn
application = app

