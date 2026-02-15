import os
import sys
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("WSGI Startup Diagnostics")
logger.info("=" * 60)

try:
    logger.info("Python version: " + sys.version)
    
    # Check environment
    logger.info("Environment variables:")
    logger.info(f"  FLASK_ENV: {os.environ.get('FLASK_ENV', 'not set')}")
    logger.info(f"  MONGODB_URI: {os.environ.get('MONGODB_URI', 'not set')[:50]}...")
    logger.info(f"  PORT: {os.environ.get('PORT', '8000')}")
    
    # Import app
    logger.info("Importing app...")
    from app import app
    logger.info("✓ App imported successfully")
    
    # Check routes
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    logger.info(f"✓ Routes registered: {len(routes)}")
    for route in sorted(routes):
        logger.info(f"    {route}")
    
    logger.info("=" * 60)
    logger.info("✓ WSGI app ready for gunicorn")
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
